import os
import clang.cindex
from dataclasses import dataclass
from typing import List


@dataclass
class UsageInfo:
    file: str
    line: int
    column: int


@dataclass
class FunctionInfo:
    start_line: int
    end_line: int
    file_abs_path: str
    file_rel_path: str
    usages: List[UsageInfo]


class CodeAnalyzer:
    def __init__(self, linux_src_path):
        self.linux_src_path = os.path.normpath(linux_src_path)
        self.src_files = {}

        self.functions = {}
        self.internal_functions = {}

    def _get_files(self, root_dir, base_dir):
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                _, ext = os.path.splitext(file)
                if ext in ['.h', '.c', '.cc', '.cpp']:
                    absolute_path = os.path.join(root, file)
                    relative_path = os.path.relpath(absolute_path, base_dir)
                    self.src_files[relative_path] = absolute_path
        print(f'Total number of src files: {len(self.src_files)}')

    def _get_linux_src_file_paths(self):
        self._get_files(self.linux_src_path, self.linux_src_path)

    def _get_added_driver_files(self):
        pre_existing_dirs_in_linux = ['accessibility', 'dax', 'interconnect', 'nvdimm', 'scsi', 'acpi', 'dca', 'iommu', 'nvme', 'sh', 'amba', 'devfreq', 'ipack', 'nvmem', 'siox', 'android', 'dio', 'irqchip', 'of', 'slimbus', 'ata', 'dma', 'isdn', 'opp', 'soc', 'atm', 'dma-buf', 'Kconfig', 'parisc', 'soundwire', 'auxdisplay', 'edac', 'parport', 'spi', 'base', 'eisa', 'leds', 'pci', 'spmi', 'bcma', 'extcon', 'macintosh', 'pcmcia', 'ssb', 'block', 'firewire', 'mailbox', 'peci', 'staging', 'bluetooth', 'firmware', 'Makefile', 'perf', 'target', 'fpga', 'mcb', 'phy', 'tc', 'built-in.a', 'fsi', 'md', 'pinctrl', 'tee', 'bus', 'gnss', 'media', 'platform', 'thermal', 'gpio', 'memory', 'pnp', 'thunderbolt', 'cdrom', 'gpu', 'memstick', 'power', 'tty', 'char', 'greybus', 'message', 'powercap', 'ufs', 'clk', 'hid', 'mfd', 'pps', 'uio', 'clocksource', 'hsi', 'misc', 'ps3', 'usb', 'comedi', 'hte', 'mmc', 'ptp', 'vdpa', 'connector', 'hv', 'modules.order', 'pwm', 'vfio', 'counter', 'hwmon', 'most', 'rapidio', 'vhost', 'cpufreq', 'hwspinlock', 'mtd', 'ras', 'video', 'cpuidle', 'hwtracing', 'mux', 'regulator', 'virt', 'i2c', 'net', 'remoteproc', 'virtio', 'i3c', 'nfc', 'reset', 'vlynq', 'idle', 'rpmsg', 'w1', 'iio', 'rtc', 'watchdog', 'crypto', 'infiniband', 'ntb', 's390', 'xen', 'cxl', 'input', 'nubus', 'sbus', 'zorro']

        driver_dir = os.path.join(self.linux_src_path, 'drivers')
        for item in os.listdir(driver_dir):
            dir_path = os.path.join(driver_dir, item)
            if not os.path.isdir(dir_path):
                continue
            if item in pre_existing_dirs_in_linux:
                continue
            self._get_files(dir_path, self.linux_src_path)

    def _parse_source_file(self, absolute_file_path):
        index = clang.cindex.Index.create()
        translation_unit = index.parse(absolute_file_path)
        return translation_unit

    #Todo: Attemp to solve namespace (Currently Unused)
    def _get_context(self, node):
        context = []
        current = node.semantic_parent
        while current and current.kind != clang.cindex.CursorKind.TRANSLATION_UNIT:
            context.append(current.spelling)
            current = current.semantic_parent
        return "::".join(reversed(context))

    def _internal_function_name(self, function_name, file_rel_path):
        return f'{file_rel_path}::{function_name}'

    def _find_function_definition(self, src_node, src_file_abs_path, src_file_rel_path):
        for child in src_node.get_children():
            if child.kind != clang.cindex.CursorKind.FUNCTION_DECL:
                continue
            if not child.is_definition():
                continue
            if str(child.location.file) != src_file_abs_path:
                continue
            start_line = child.extent.start.line - 1
            end_line = child.extent.end.line - 1

            #print(f'{child.spelling} {child.is_definition()} {child.kind} {child.linkage} {child.location.file}')
            if child.linkage == clang.cindex.LinkageKind.INTERNAL:
                key = self._internal_function_name(child.spelling, src_file_rel_path)
                if key in self.internal_functions:
                    print(f"[WARNING!] Internal function {key} already exists")
                self.internal_functions[key] = FunctionInfo(start_line, end_line, src_file_abs_path, src_file_rel_path, [])
            else:
                if child.spelling in self.functions:
                    print(f"[WARNING!] function {child.spelling} already exists")
                self.functions[child.spelling] = FunctionInfo(start_line, end_line, src_file_abs_path, src_file_rel_path, [])

    def _find_function_usage(self, node):
        if node.kind == clang.cindex.CursorKind.CALL_EXPR:
            usage = node.location
            function_name = node.spelling
            internal_function_name = self._internal_function_name(function_name, os.path.relpath(str(usage.file), self.linux_src_path))
            if internal_function_name in self.internal_functions:
                self.internal_functions[internal_function_name].usages.append(UsageInfo(usage.file.name, usage.line, usage.column))
            elif function_name in self.functions:
                self.functions[function_name].usages.append(UsageInfo(usage.file.name, usage.line, usage.column))

        for child in node.get_children():
            self._find_function_usage(child)

    def _analyze(self):
        for rel_path, abs_path in self.src_files.items():
            tu = self._parse_source_file(abs_path)
            self._find_function_definition(tu.cursor, abs_path, rel_path)

        for rel_path, abs_path in self.src_files.items():
            tu = self._parse_source_file(abs_path)
            self._find_function_usage(tu.cursor)

    def analyze_driver_code(self):
        self._get_added_driver_files()
        self._analyze()

    def _generate_usage_str(self, usages):
        usage_str = f'Found {len(usages)} usages:\n'
        for usage in usages:
            usage_str += f'\t-{usage.file} {usage.line} {usage.column}\n'
        return usage_str

    def get_function_usage(self, function_name, file_path):
        """
        [Experimental] This function only works on device driver source files that are added to the existing Linux kernel (excluding the device drivers that already exist).

        Retrieve the usage information of a specified function within a given file path.

        This method looks up the usage of a function defined in the file specified by file_path.
        If the file does not exist or the function does not exist, it returns an error message.
        Otherwise, it returns the usage information of the function.

        Parameters:
        - function_name (str): The name of the function to retrieve usage information for.
        - file_path (str): The relative file path from the source root where the function is defined.

        Returns:
        - str: The usage information of the function if found, otherwise an error message.

        The returned string format is:
        "Found n usages
        - Filename line column"
        """
        if file_path not in self.src_files:
            return f"File {file_path} does not exist"

        internal_function_name = self._internal_function_name(function_name, file_path)
        if internal_function_name in self.internal_functions:
            usages = self.internal_functions[internal_function_name].usages
            return self._generate_usage_str(usages)
        if function_name in self.functions:
            usages = self.functions[function_name].usages
            return self._generate_usage_str(usages)
        return f"Function {function_name} does not exist in file {file_path}"

    def get_get_function_usage_tool(self):
        return self.get_function_usage, {
            "type": "function",
            "function": {
                "name": "get_function_usage",
                "description": self.get_function_usage.__doc__,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "function_name": {
                            "type": "string",
                            "description": "The name of the function to retrieve usage information for.",
                        },
                        "file_path": {
                            "type": "string",
                            "description": "The relative file path from the source root where the function is defined.",
                        }
                    },
                    "required": ["function_name", "file_path"],
                },
            }
        }

package main

func getSyzmapTester(harness string) map[uint64]string {
	// For testing
	calls0 := calls[harness]
	syzmap := make(map[uint64]string)
	for i := 0; i < len(calls0); i++ {
		idx := getIdx(harness, uint64(i))
		syzmap[idx] = calls0[i]
	}
	return syzmap
}

func getIdx(harness string, i uint64) uint64 {
	switch harness {
	case "NRFIN-00001":
		i += (0xdeadbeef + 1)
	case "KPRCA-00001":
		if i == 0 || i == 1 {
			i += 0x40
		} else {
			i = 0x50
		}
	case "BRAD-OBERBERG":
		i += (0x77617363 + 2)
	case "CROMU-00003":
		if 0 <= i && i <= 6 {
			i += 0x40
		} else {
			i += 0x4a
		}
	case "CROMU-00001":
		i = []uint64{
			0xc00010ff, 0x1337beef, 0x13370001, 0x13370002,
			0x13370003, 0x13370004, 0x13370005, 0x13370006,
		}[int(i)]
	}
	return i
}

var calls = map[string][]string{
	"linux_test": {
		"syz_harness$linux_test_harness_cmd0",
		"syz_harness$linux_test_harness_cmd1",
	},
	"NRFIN-00001": {
		"syz_harness$nrfin_00001_cmd1",
		"syz_harness$nrfin_00001_cmd2",
		"syz_harness$nrfin_00001_cmd3",
		"syz_harness$nrfin_00001_cmd4",
		"syz_harness$nrfin_00001_cmd5",
		"syz_harness$nrfin_00001_cmd6",
	},
	"KPRCA-00001": {
		"syz_harness$kprca_00001_cmd1",
		"syz_harness$kprca_00001_cmd2",
		"syz_harness$kprca_00001_cmd3",
	},
	"CVE-2023-2513": {
		"syz_harness$cve_2023_2513_cmd0",
		"syz_harness$cve_2023_2513_cmd1",
		"syz_harness$cve_2023_2513_cmd2",
		"syz_harness$cve_2023_2513_cmd3",
		"syz_harness$cve_2023_2513_cmd4",
	},
	"CVE-2022-32250": {
		"syz_harness$cve_2022_32250_cmd0",
		"syz_harness$cve_2022_32250_cmd1",
	},
	"CVE-2022-0995": {
		"syz_harness$cve_2022_0995_cmd0",
		"syz_harness$cve_2022_0995_cmd1",
	},
	"CVE-2021-38208": {
		"syz_harness$cve_2021_38208_cmd0",
		"syz_harness$cve_2021_38208_cmd1",
		"syz_harness$cve_2021_38208_cmd2",
		"syz_harness$cve_2021_38208_cmd3",
	},
	"CVE-2022-0185": {
		"syz_harness$cve_2022_0185_cmd0",
		"syz_harness$cve_2022_0185_cmd1",
		"syz_harness$cve_2022_0185_cmd2",
		"syz_harness$cve_2022_0185_cmd3",
		"syz_harness$cve_2022_0185_cmd4",
		"syz_harness$cve_2022_0185_cmd5",
		"syz_harness$cve_2022_0185_cmd6",
	},
	"CROMU-00001": {
		"syz_harness$cromu_00001_cmd_create",
		"syz_harness$cromu_00001_cmd_login",
		"syz_harness$cromu_00001_cmd_exit",
		"syz_harness$cromu_00001_cmd_send_msg",
		"syz_harness$cromu_00001_cmd_read_msg",
		"syz_harness$cromu_00001_cmd_list_msg",
		"syz_harness$cromu_00001_cmd_del_msg",
		"syz_harness$cromu_00001_cmd_logout",
	},
	"CROMU-00004": {
		"syz_harness$cromu_00004_cmd0",
	},
	"CROMU-00003": {
		"syz_harness$cromu_00003_cmd_yolo_add",
		"syz_harness$cromu_00003_cmd_yolo_del",
		"syz_harness$cromu_00003_cmd_yolo_edit",
		"syz_harness$cromu_00003_cmd_yolo_show",
		"syz_harness$cromu_00003_cmd_yolo_list",
		"syz_harness$cromu_00003_cmd_yolo_sort",
		"syz_harness$cromu_00003_cmd_yolo_exit",
		"syz_harness$cromu_00003_cmd_yolo_show_q",
		"syz_harness$cromu_00003_cmd_yolo_show_d",
		"syz_harness$cromu_00003_cmd_yolo_show_e",
		"syz_harness$cromu_00003_cmd_yolo_show_n",
		"syz_harness$cromu_00003_cmd_yolo_show_p",
	},
	"CROMU-00005": {
		"syz_harness$cromu_00005_cmd0",
	},
	"CADET-00001": {
		"syz_harness$cadet_00001_cmd1",
	},
	"BRAD-OBERBERG": {
		"syz_harness$brad_oberberg_cmd_read",
		"syz_harness$brad_oberberg_cmd_write",
		"syz_harness$brad_oberberg_cmd_get_consumer",
		"syz_harness$brad_oberberg_cmd_set_consumer",
		"syz_harness$brad_oberberg_cmd_get_stats",
	},
}

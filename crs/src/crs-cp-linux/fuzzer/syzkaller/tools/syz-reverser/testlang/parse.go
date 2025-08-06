package testlang

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"unicode"
)

const (
	ASSIGN = "::="
	OR     = "|"
	SIZE   = "size"
	VALUE  = "value"
	TYPE   = "type"
)

func split2(str string, sep string) []string {
	ret := strings.Split(str, sep)
	if len(ret) != 2 {
		panic("split 2 fail")
	}
	return ret
}

func allowedName(c rune) bool {
	return unicode.IsLetter(c) || unicode.IsDigit(c) || c == '_'
}

func parseName(line *string) string {
	tmp := *line
	for i, c := range tmp {
		if !allowedName(c) {
			name := tmp[:i]
			*line = strings.TrimSpace(tmp[i:])
			return name
		}
	}
	name := tmp
	*line = ""
	return name
}

func parseUint(line string) (uint64, error) {
	if strings.HasPrefix(line, "0x") {
		return strconv.ParseUint(line[2:], 16, 64)
	} else {
		return strconv.ParseUint(line, 10, 64)
	}
}

func parseSize(line string) Size {
	size, err := parseUint(line)
	if err == nil {
		return FixedSize{uint32(size)}
	}
	return NamedSize{parseName(&line)}
}

func parseAttr(f *NormalField, line string) {
	for _, attr := range strings.Split(line, ",") {
		tmp := split2(strings.TrimSpace(attr), ":")
		value := strings.TrimSpace(tmp[1])
		switch strings.TrimSpace(tmp[0]) {
		case SIZE:
			size := parseSize(value)
			f.size = &size
		case VALUE:
			value, err := parseUint(value)
			if err != nil {
				fmt.Println(err)
			}
			f.value = &value
		case TYPE:
			f.fieldType = &value
		default:
			panic("parseAttr error")
		}
	}
}

func parseField(line string) Field {
	line = strings.TrimSpace(line)
	name := parseName(&line)
	size := len(line)
	if size == 0 {
		return RefField{name}
	}
	if line[0] == '[' && line[size-1] == ']' {
		line = line[1 : size-1]
		cnt := parseSize(line)
		return ArrayField{name, &cnt}
	}
	if line[0] == '{' && line[size-1] == '}' {
		f := NormalField{name, nil, nil, nil}
		parseAttr(&f, line[1:size-1])
		return f
	}
	panic("parseField error")
}

func Parse(txt string) *TestLang {
	lang := TestLang{}
	var cur *Record
	for _, line := range strings.Split(txt, "\n") {
		line = strings.Split(line, "//")[0]
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		if strings.Contains(line, ASSIGN) {
			tmp := split2(line, ASSIGN)
			name := strings.TrimSpace(tmp[0])
			f := parseField(tmp[1])
			cur = &Record{name, []Field{f}, false}
			lang.addRecord(cur)
		} else if strings.HasPrefix(line, OR) {
			cur.setUnion()
			line = split2(line, OR)[1]
			cur.addField(parseField(line))
		} else {
			cur.addField(parseField(line))
		}
	}
	return &lang
}

func ParseFile(fname *string) *TestLang {
	data, err := os.ReadFile(*fname)
	if err != nil {
		panic(err)
	}
	return Parse(string(data))
}

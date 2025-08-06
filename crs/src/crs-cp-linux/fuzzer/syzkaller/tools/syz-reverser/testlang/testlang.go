package testlang

import (
	"fmt"
	"strings"
)

const (
	InputName        = "INPUT"
	CommandName      = "COMMAND"
	CommandCountName = "COMMAND_CNT"
)

type TestLang struct {
	records []*Record
}

type Record struct {
	name    string
	fields  []Field
	isUnion bool
}

type Field interface {
	String() string
}

type Size interface {
	String() string
}

type FixedSize struct {
	size uint32
}

type NamedSize struct {
	name string
}

type NormalField struct {
	name      string
	fieldType *string
	size      *Size
	value     *uint64
}

type ArrayField struct {
	itemType string
	cnt      *Size
}

type RefField struct {
	name string
}

func (r *Record) setUnion() {
	r.isUnion = true
}

func (r *Record) addField(f Field) {
	r.fields = append(r.fields, f)
}

func (lang *TestLang) addRecord(r *Record) {
	lang.records = append(lang.records, r)
}

func (size FixedSize) String() string {
	return fmt.Sprintf("%d", size.size)
}

func (size NamedSize) String() string {
	return size.name
}

func (f NormalField) String() string {
	ret := f.name
	ret += " {"
	if f.size != nil {
		ret += "size: " + (*f.size).String()
	}
	if f.value != nil {
		if f.size != nil {
			ret += ", "
		}
		ret += "value: " + fmt.Sprintf("%d", *f.value)
	}
	if f.fieldType != nil {
		if f.size != nil || f.value != nil {
			ret += ", "
		}
		ret += "type: " + (*f.fieldType)
	}
	ret += "}"
	return ret
}

func (f ArrayField) String() string {
	ret := f.itemType
	ret += "["
	if f.cnt != nil {
		ret += (*f.cnt).String()
	}
	ret += "]"
	return ret
}

func (f RefField) String() string {
	return f.name
}

func (r Record) String() string {
	ret := r.name + " ::= "
	pre := strings.Repeat(" ", len(ret)-2)
	if r.isUnion {
		pre += "| "
	} else {
		pre += "  "
	}
	ret += r.fields[0].String() + "\n"
	for _, f := range r.fields[1:] {
		ret += pre + f.String() + "\n"
	}
	return ret
}

func (lang TestLang) String() string {
	ret := ""
	for _, r := range lang.records {
		ret += r.String() + "\n"
	}
	return ret
}

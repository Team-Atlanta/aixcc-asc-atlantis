package testlang

import (
	"path"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestHelloEmpty(t *testing.T) {
	_, this_path, _, _ := runtime.Caller(0)
	target := path.Join(path.Dir(this_path), "../../../../reverser/answers/")
	files, _ := filepath.Glob(target + "/*.txt")
	for _, f := range files {
		if strings.Contains(f, "bad") {
			continue
		}
		lang1 := ParseFile(&f)
		str1 := lang1.String()
		t.Logf("\n" + str1)
		lang2 := Parse(str1)
		str2 := lang2.String()
		if str1 != str2 {
			t.Fatalf("Fail: " + f)
		}
	}
}

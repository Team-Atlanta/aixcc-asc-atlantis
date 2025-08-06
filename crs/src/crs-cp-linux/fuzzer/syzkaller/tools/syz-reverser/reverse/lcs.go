package reverse

import "sort"

type substr struct {
	beg int
	end int
}

func (s substr) len() int {
	return s.end - s.beg
}

type commonSubstr struct {
	s1 substr
	s2 substr
}

// Returns the set of non-overlapping LCS (Longest Common Substring)
// TODO: Do this in bits
func getLongestCommonSubstr(bytes1, bytes2 []byte) []commonSubstr {
	dp := make([]int, len(bytes2))
	lcses := make([]commonSubstr, len(bytes2))
	for i1, b1 := range bytes1 {
		for i2 := len(bytes2) - 1; i2 >= 0; i2-- {
			b2 := bytes2[i2]
			if b1 == b2 {
				if i2 == 0 {
					dp[i2] = 1
				} else {
					dp[i2] = dp[i2-1] + 1
				}
				if dp[i2] > lcses[i2].s1.len() {
					lcses[i2].s1 = substr{
						beg: i1 - dp[i2] + 1,
						end: i1 + 1,
					}
					lcses[i2].s2 = substr{
						beg: i2 - dp[i2] + 1,
						end: i2 + 1,
					}
				}
			} else {
				dp[i2] = 0
			}
		}
	}
	sort.Slice(lcses, func(i, j int) bool {
		return lcses[i].s1.len() > lcses[j].s1.len()
	})
	ret := []commonSubstr{}
	for _, cs1 := range lcses {
		if cs1.s1.len() == 0 {
			continue
		}
		overlapped := false
		for _, cs2 := range ret {
			if !(cs2.s1.end <= cs1.s1.beg || cs1.s1.end <= cs2.s1.beg) {
				overlapped = true
				break
			}
		}
		if !overlapped {
			ret = append(ret, cs1)
		}
	}
	return ret
}

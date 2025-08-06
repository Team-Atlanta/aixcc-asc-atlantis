#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

// The following line is needed for shared memory testcase fuzzing
__AFL_FUZZ_INIT();

void vuln(char *buf) {
  if (strcmp(buf, "vuln") == 0) { abort(); }
}

typedef struct {
  char name[12];
  char data[12];
} note_t;

int main(int argc, char **argv) {
  // Start the forkserver at this point (i.e., forks will happen here)
  __AFL_INIT();
  // The following line is also needed for shared memory testcase fuzzing
  unsigned char *buf = __AFL_FUZZ_TESTCASE_BUF;  // must be after __AFL_INIT
  int length = __AFL_FUZZ_TESTCASE_LEN;

  // commands
  // add note 0x0 // [4:opcode] [1:idx] [11:name]
  // read note 0x1 // [4:opcode] [1:idx]
  // write note 0x2 // [4:opcode] [1:idx] [11:data]
  // delete note 0x3 // [4:opcode] [1:idx]

  note_t *notes[256];
  uint32_t opcode, count;
  uint8_t index;

  memcpy(&count, buf, 4);
  buf += 4;

  for (int i = 0; i + 16 <= length && (i >> 4) < count; i += 16) {
    memcpy(&opcode, &buf[i], 4);
    memcpy(&index, &buf[i + 4], 1);
    char* data = &buf[i + 5];

    switch (opcode) {
      case 0:
        notes[index] = malloc(sizeof(note_t));
        strcpy(notes[index]->name, data);
        notes[index]->data[0] = '0';
        break;
      case 1:
        printf("Note %d: \nTitle: %s\n Data: %s\n", index, notes[index]->name, notes[index]->data);
        break;
      case 2:
        strcpy(notes[index]->data, data);
        break;
      case 3:
        free(notes[index]);
        break;
      default:
        puts("unknown command");
        break;
    }
  }

  return 0;
}
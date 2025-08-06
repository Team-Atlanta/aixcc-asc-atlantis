#define _GNU_SOURCE

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <stdlib.h>
#include <fcntl.h>
#include <err.h>
#include <stdbool.h>

#include <sys/types.h>
#include <sys/stat.h>
#include <sys/ioctl.h>


#define MAX_STDOUT      1024

/* interface to the device driver */
typedef struct {
  int action;

  /* lookup */
  char first[32];
  char last[32];
  char phone[14];
  char office[6];
  char gender[2];
  char hacker[2];

  /* edit */
  char new_phone[14];
  char new_first[32];
  char new_last[32];
  char new_office[6];
  char new_gender[2];
  char new_hacker[2];

  /* show */
  int show_action;

  char stdout[MAX_STDOUT];
} req_t;

#define YOLO_ADD 0x40
#define YOLO_DEL 0x41
#define YOLO_EDIT 0x42
#define YOLO_SHOW 0x43
#define YOLO_LIST 0x44
#define YOLO_SORT 0x45
#define YOLO_EXIT 0x46

#define YOLO_SHOW_Q 0x51
#define YOLO_SHOW_D 0x52
#define YOLO_SHOW_E 0x53
#define YOLO_SHOW_N 0x54
#define YOLO_SHOW_P 0x55

req_t req;

void print_req(){
  if(req.action >= 0x40 && req.action <= 0x46){
    const char* cmd_str[] = {"YOLO_ADD", "YOLO_DEL", "YOLO_EDIT", "YOLO_SHOW", "YOLO_LIST", "YOLO_SORT", "YOLO_EXIT"};
    printf("[INFO] action: %s \n", cmd_str[req.action - 0x40]);
  }
  else if (req.action >= 0x51 && req.action <= 0x55){
    const char* cmd_str[] = {"YOLO_SHOW_Q", "YOLO_SHOW_D", "YOLO_SHOW_E", "YOLO_SHOW_N", "YOLO_SHOW_P"};
    printf("[INFO] action: %s \n", cmd_str[req.action - 0x51]);
  }
  else{
    printf("[ERROR] unknown action: %x \n", req.action);
  }
  printf("[INFO] first(%s) last(%s) phone(%s) office(%s) gender(%s) hacker(%s) \n", req.first, req.last, req.phone, req.office, req.gender, req.hacker);
  printf("[INFO] new_first(%s) new_last(%s) new_phone(%s) new_office(%s) new_gender(%s) new_hacker(%s) \n", req.new_first, req.new_last, req.new_phone, req.new_office, req.new_gender, req.new_hacker);
}

size_t min(size_t size1, size_t size2){
  return size1 < size2 ? size1 : size2;
}

int yolo_add(int fd, char *first, char *last, char *phone,
    unsigned short office, char gender, bool hacker) {
  memset(&req, 0, sizeof(req_t));

  req.action = YOLO_ADD;
  memcpy(req.first, first, min(sizeof(req.first), strlen(first)));
  memcpy(req.last, last, min(sizeof(req.last), strlen(last)));
  memcpy(req.phone, phone, min(sizeof(req.phone), strlen(phone)));
  snprintf(req.office, sizeof(req.office), "%hu", office);
  req.gender[0] = gender;
  req.hacker[0] = hacker ? 'y' : 'n';

  print_req();
  int ret = ioctl(fd, req.action, &req);
  printf("[INFO][yolo_add] %s \n", req.stdout);
  return ret;
}

int yolo_del(int fd, char *first, char *last) {
  memset(&req, 0, sizeof(req_t));

  req.action = YOLO_DEL;
  memcpy(req.first, first, min(sizeof(req.first), strlen(first)));
  memcpy(req.last, last, min(sizeof(req.last), strlen(last)));

  print_req();
  int ret = ioctl(fd, req.action, &req);
  printf("[INFO][yolo_del] %s \n", req.stdout);
  return ret;
}

int yolo_edit(int fd, char *first, char *last,
    char *new_first, char *new_last, char *new_phone,
    unsigned short new_office, char new_gender, bool new_hacker) {
  memset(&req, 0, sizeof(req_t));

  req.action = YOLO_EDIT;
  memcpy(req.first, first, min(sizeof(req.first), strlen(first)));
  memcpy(req.last, last, min(sizeof(req.last), strlen(last)));

  memcpy(req.new_first, new_first, min(sizeof(req.new_first), strlen(new_first)));
  memcpy(req.new_last, new_last, min(sizeof(req.new_last), strlen(new_last)));
  memcpy(req.new_phone, new_phone, min(sizeof(req.new_phone), strlen(new_phone)));
  snprintf(req.new_office, sizeof(req.new_office), "%hu", new_office);
  req.new_gender[0] = new_gender;
  req.new_hacker[0] = new_hacker ? 'y' : 'n';

  print_req();
  int ret = ioctl(fd, req.action, &req);
  printf("[INFO][yolo_edit] %s \n", req.stdout);
  return ret;
}

int yolo_show(int fd, char *first, char *last) {
  memset(&req, 0, sizeof(req_t));

  req.action = YOLO_SHOW;
  memcpy(req.first, first, min(sizeof(req.first), strlen(first)));
  memcpy(req.last, last, min(sizeof(req.last), strlen(last)));

  print_req();
  int ret = ioctl(fd, req.action, &req);
  printf("[INFO][yolo_show] %s \n", req.stdout);
  return ret;
}

int yolo_show_q(int fd) {
  memset(&req, 0, sizeof(req_t));

  req.action = YOLO_SHOW_Q;

  print_req();
  int ret = ioctl(fd, req.action, &req);
  printf("[INFO][yolo_show_q] %s \n", req.stdout);
  return ret;
}

int yolo_show_d(int fd) {
  memset(&req, 0, sizeof(req_t));

  req.action = YOLO_SHOW_D;

  print_req();
  int ret = ioctl(fd, req.action, &req);
  printf("[INFO][yolo_show_d] %s \n", req.stdout);
  return ret;
}

int yolo_show_e(int fd, char *new_first, char *new_last, char *new_phone,
    unsigned short new_office, char new_gender, bool new_hacker) {
  memset(&req, 0, sizeof(req_t));

  req.action = YOLO_SHOW_E;
  
  memcpy(req.new_first, new_first, min(sizeof(req.new_first), strlen(new_first)));
  memcpy(req.new_last, new_last, min(sizeof(req.new_last), strlen(new_last)));
  memcpy(req.new_phone, new_phone, min(sizeof(req.new_phone), strlen(new_phone)));
  snprintf(req.new_office, sizeof(req.new_office), "%hu", new_office);
  req.new_gender[0] = new_gender;
  req.new_hacker[0] = new_hacker ? 'y' : 'n';

  print_req();
  int ret = ioctl(fd, req.action, &req);
  printf("[INFO][yolo_show_e] %s \n", req.stdout);
  return ret;
}

int yolo_show_n(int fd) {
  memset(&req, 0, sizeof(req_t));

  req.action = YOLO_SHOW_N;

  print_req();
  int ret = ioctl(fd, req.action, &req);
  printf("[INFO][yolo_show_n] %s \n", req.stdout);
  return ret;
}

int yolo_show_p(int fd) {
  memset(&req, 0, sizeof(req_t));

  req.action = YOLO_SHOW_P;

  print_req();
  int ret = ioctl(fd, req.action, &req);
  printf("[INFO][yolo_show_p] %s \n", req.stdout);
  return ret;
}

int yolo_list(int fd) {
  memset(&req, 0, sizeof(req_t));

  req.action = YOLO_LIST;

  print_req();
  int ret = ioctl(fd, req.action, &req);
  printf("[INFO][yolo_list] %s \n", req.stdout);
  return ret;
}

int yolo_sort(int fd) {
  memset(&req, 0, sizeof(req_t));

  req.action = YOLO_SORT;

  print_req();
  int ret = ioctl(fd, req.action, &req);
  printf("[INFO][yolo_sort] %s \n", req.stdout);
  return ret;
}

int yolo_exit(int fd) {
  memset(&req, 0, sizeof(req_t));

  req.action = YOLO_EXIT;

  print_req();
  int ret = ioctl(fd, req.action, &req);
  printf("[INFO][yolo_exit] %s \n", req.stdout);
  return ret;
}


/***
 * Blob begins with a 4 byte command count
 * [4-bytes command count]
 * Currently there are eight commands:
 *  YOLO_ADD      - add contact
 *                  [4-bytes first_name_size][first_name_size-bytes first_name data]
 *                  [4-bytes last_name_size][last_name_size-bytes last_name data]
 *                  [4-bytes phone_size][phone_size-bytes phone data]
 *                  [2-bytes office][1-byte gender][1-byte hacker_bool]
 *  YOLO_DEL      - add contact
 *                  [4-bytes first_name_size][first_name_size-bytes first_name data]
 *                  [4-bytes last_name_size][last_name_size-bytes last_name data]
 *  YOLO_EDIT     - edit contact
 *                  [4-bytes old_first_name_size][old_first_name_size-bytes oldfirst_name data]
 *                  [4-bytes old_last_name_size][old_last_name_size-bytes old_last_name data]
 *                  [4-bytes first_name_size][first_name_size-bytes first_name data]
 *                  [4-bytes last_name_size][last_name_size-bytes last_name data]
 *                  [4-bytes phone_size][phone_size-bytes phone data]
 *                  [2-bytes office][1-byte gender][1-byte hacker_bool]
 *  YOLO_SHOW     - show
 *                  [4-bytes first_name_size][first_name_size-bytes first_name data]
 *                  [4-bytes last_name_size][last_name_size-bytes last_name data]
 *  YOLO_SHOW_Q   - show_q
 *                  [None]
 *  YOLO_SHOW_D   - show_d
 *                  [None]
 *  YOLO_SHOW_E   - show_e
 *                  [4-bytes first_name_size][first_name_size-bytes first_name data]
 *                  [4-bytes last_name_size][last_name_size-bytes last_name data]
 *                  [4-bytes phone_size][phone_size-bytes phone data]
 *                  [2-bytes office][1-byte gender][1-byte hacker_bool]
 *  YOLO_SHOW_N   - show_n
 *                  [None]
 *  YOLO_SHOW_P   - show_p
 *                  [None]
 *  YOLO_LIST     - list
 *                  [None]
 *  YOLO_SORT     - sort
 *                  [None]
 *  YOLO_EXIT     - exit
 *                  [None]
 *
 * blob_size MUST be a trusted value
 */
int harness( uint8_t *blob, uint32_t blob_size)
{
  int index = 0;
  uint32_t command, command_count = 0;
  uint32_t size = 0;

  int fd = -1;
  char* old_first = NULL;
  char* old_last = NULL;
  char* first = NULL;
  char* last = NULL;
  char* phone = NULL;
  uint16_t office = 0;
  char gender = 0;
  bool hacker_bool = 0;

  printf("[INFO] harness blob_size %u \n", blob_size);

  if ( blob == NULL ) {
    return -1;
  }
  if((fd = open("/dev/CROMU-00003", O_RDONLY)) < 0) {
    printf("[ERROR] unable to open CROMU-00003 \n");
    return -1;
  }

  if ( blob_size < 4 ) {
    close(fd);
    return -1;
  }

  memcpy(&command_count, blob, 4);
  index += 4;

  printf("[INFO] Executing %d commands\n", command_count);
  for ( uint32_t i = 0; i < command_count; i++) {
    if ( blob_size - index < 4 ) {
      printf("[ERROR] ran out of commands\n");
      close(fd);
      return -1;
    }

    memcpy(&command, blob + index, 4);
    index += 4;

    switch ( command ) {
      case YOLO_ADD:
        //read first name size and first name
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_ADD error\n");
          close(fd);
          return -1;
        }
        memcpy(&size, blob + index, 4);
        index += 4;
        if ( blob_size - index < size ) {
          printf("[ERROR] YOLO_ADD error\n");
          close(fd);
          return -1;
        }
        first = blob + index;
        index += size;
        //read last name size and last name
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_ADD error\n");
          close(fd);
          return -1;
        }
        memcpy(&size, blob + index, 4);
        index += 4;
        if ( blob_size - index < size ) {
          printf("[ERROR] YOLO_ADD error\n");
          close(fd);
          return -1;
        }
        last = blob + index;
        index += size;
        //read phone size and phone
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_ADD error\n");
          close(fd);
          return -1;
        }
        memcpy(&size, blob + index, 4);
        index += 4;
        if ( blob_size - index < size ) {
          printf("[ERROR] YOLO_ADD error\n");
          close(fd);
          return -1;
        }
        phone = blob + index;
        index += size;
        //read office, gender, hacker_bool
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_ADD error\n");
          close(fd);
          return -1;
        }
        memcpy(&office, blob + index, 2);
        memcpy(&gender, blob + index + 2, 1);
        memcpy(&hacker_bool, blob + index + 3, 1);
        index += 4;

        if (yolo_add(fd, first, last, phone, office, gender, hacker_bool) < 0) {
          printf("[ERROR] YOLO_ADD error\n");
          close(fd);
          return -1;
        }
        break;
      case YOLO_DEL:
        //read first name size and first name
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_DEL error\n");
          close(fd);
          return -1;
        }
        memcpy(&size, blob + index, 4);
        index += 4;
        if ( blob_size - index < size ) {
          printf("[ERROR] YOLO_DEL error\n");
          close(fd);
          return -1;
        }
        first = blob + index;
        index += size;
        //read last name size and last name
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_DEL error\n");
          close(fd);
          return -1;
        }
        memcpy(&size, blob + index, 4);
        index += 4;
        if ( blob_size - index < size ) {
          printf("[ERROR] YOLO_DEL error\n");
          close(fd);
          return -1;
        }
        last = blob + index;
        index += size;

        if (yolo_del(fd, first, last) < 0) {
          printf("[ERROR] YOLO_DEL error\n");
          close(fd);
          return -1;
        }
        break;
      case YOLO_EDIT:
        //read old first name size and old first name
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_EDIT error\n");
          close(fd);
          return -1;
        }
        memcpy(&size, blob + index, 4);
        index += 4;
        if ( blob_size - index < size ) {
          printf("[ERROR] YOLO_EDIT error\n");
          close(fd);
          return -1;
        }
        old_first = blob + index;
        index += size;
        //read old last name size and old last name
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_EDIT error\n");
          close(fd);
          return -1;
        }
        memcpy(&size, blob + index, 4);
        index += 4;
        if ( blob_size - index < size ) {
          printf("[ERROR] YOLO_EDIT error\n");
          close(fd);
          return -1;
        }
        old_last = blob + index;
        index += size;
        //read first name size and first name
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_EDIT error\n");
          close(fd);
          return -1;
        }
        memcpy(&size, blob + index, 4);
        index += 4;
        if ( blob_size - index < size ) {
          printf("[ERROR] YOLO_EDIT error\n");
          close(fd);
          return -1;
        }
        first = blob + index;
        index += size;
        //read last name size and last name
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_EDIT error\n");
          close(fd);
          return -1;
        }
        memcpy(&size, blob + index, 4);
        index += 4;
        if ( blob_size - index < size ) {
          printf("[ERROR] YOLO_EDIT error\n");
          close(fd);
          return -1;
        }
        last = blob + index;
        index += size;
        //read phone size and phone
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_EDIT error\n");
          close(fd);
          return -1;
        }
        memcpy(&size, blob + index, 4);
        index += 4;
        if ( blob_size - index < size ) {
          printf("[ERROR] YOLO_EDIT error\n");
          close(fd);
          return -1;
        }
        phone = blob + index;
        index += size;
        //read office, gender, hacker_bool
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_EDIT error\n");
          close(fd);
          return -1;
        }
        memcpy(&office, blob + index, 2);
        memcpy(&gender, blob + index + 2, 1);
        memcpy(&hacker_bool, blob + index + 3, 1);
        index += 4;

        if (yolo_edit(fd, old_first, old_last, first, last, phone, office, gender, hacker_bool) < 0) {
          printf("[ERROR] YOLO_EDIT error\n");
          close(fd);
          return -1;
        }
        break;
      case YOLO_SHOW:
        //read first name size and first name
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_SHOW error\n");
          close(fd);
          return -1;
        }
        memcpy(&size, blob + index, 4);
        index += 4;
        if ( blob_size - index < size ) {
          printf("[ERROR] YOLO_SHOW error\n");
          close(fd);
          return -1;
        }
        first = blob + index;
        index += size;
        //read last name size and last name
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_SHOW error\n");
          close(fd);
          return -1;
        }
        memcpy(&size, blob + index, 4);
        index += 4;
        if ( blob_size - index < size ) {
          printf("[ERROR] YOLO_SHOW error\n");
          close(fd);
          return -1;
        }
        last = blob + index;
        index += size;

        if (yolo_show(fd, first, last) < 0) {
          printf("[ERROR] YOLO_SHOW error\n");
          close(fd);
          return -1;
        }
        break;
      case YOLO_SHOW_Q:
        if (yolo_show_q(fd) < 0) {
          printf("[ERROR] YOLO_SHOW_Q error\n");
          close(fd);
          return -1;
        }
        break;
      case YOLO_SHOW_D:
        if (yolo_show_d(fd) < 0) {
          printf("[ERROR] YOLO_SHOW_D error\n");
          close(fd);
          return -1;
        }
        break;
      case YOLO_SHOW_E:
        //read first name size and first name
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_SHOW_E error\n");
          close(fd);
          return -1;
        }
        memcpy(&size, blob + index, 4);
        index += 4;
        if ( blob_size - index < size ) {
          printf("[ERROR] YOLO_SHOW_E error\n");
          close(fd);
          return -1;
        }
        first = blob + index;
        index += size;
        //read last name size and last name
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_SHOW_E error\n");
          close(fd);
          return -1;
        }
        memcpy(&size, blob + index, 4);
        index += 4;
        if ( blob_size - index < size ) {
          printf("[ERROR] YOLO_SHOW_E error\n");
          close(fd);
          return -1;
        }
        last = blob + index;
        index += size;
        //read phone size and phone
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_SHOW_E error\n");
          close(fd);
          return -1;
        }
        memcpy(&size, blob + index, 4);
        index += 4;
        if ( blob_size - index < size ) {
          printf("[ERROR] YOLO_SHOW_E error\n");
          close(fd);
          return -1;
        }
        phone = blob + index;
        index += size;
        //read office, gender, hacker_bool
        if ( blob_size - index < 4 ) {
          printf("[ERROR] YOLO_SHOW_E error\n");
          close(fd);
          return -1;
        }
        memcpy(&office, blob + index, 2);
        memcpy(&gender, blob + index + 2, 1);
        memcpy(&hacker_bool, blob + index + 3, 1);
        index += 4;

        if (yolo_show_e(fd, first, last, phone, office, gender, hacker_bool) < 0) {
          printf("[ERROR] YOLO_SHOW_E error\n");
          close(fd);
          return -1;
        }
        break;
      case YOLO_SHOW_N:
        if (yolo_show_n(fd) < 0) {
          printf("[ERROR] YOLO_SHOW_N error\n");
          close(fd);
          return -1;
        }
        break;
      case YOLO_SHOW_P:
        if (yolo_show_p(fd) < 0) {
          printf("[ERROR] YOLO_SHOW_P error\n");
          close(fd);
          return -1;
        }
        break;
      case YOLO_LIST:
        if (yolo_list(fd) < 0) {
          printf("[ERROR] YOLO_LIST error\n");
          close(fd);
          return -1;
        }
        break;
      case YOLO_SORT:
        if (yolo_sort(fd) < 0) {
          printf("[ERROR] YOLO_SORT error\n");
          close(fd);
          return -1;
        }
        break;
      case YOLO_EXIT:
        if (yolo_exit(fd) < 0) {
          printf("[ERROR] YOLO_EXIT error\n");
          close(fd);
          return -1;
        }
        break;
      default:
        printf("[ERROR] Unknown command: %x\n", command);
        close(fd);
        return -1;
    }
  }

  close(fd);
  return 0;
}

int main(int argc, char *argv[])
{
  char *blob = NULL;
  struct stat st;
  int fd;

  printf("[INFO] main start! \n");

  if (argc < 2) {
    printf("Need file\n");
    return -1;
  }

  if ( stat(argv[1], &st) != 0) {
    printf("Failed to stat file\n");
    return -1;
  }

  fd = open(argv[1], O_RDONLY);

  if ( fd < 0 ) {
    printf("[ERROR] Failed to open file\n");
    return -1;
  }

  blob = malloc(st.st_size);

  if ( blob == NULL ) {
    printf("[ERROR] malloc failed! \n");
    return 0;
  }

  read(fd, blob, st.st_size);

  close(fd);

  harness(blob, st.st_size);

  return 0;
}

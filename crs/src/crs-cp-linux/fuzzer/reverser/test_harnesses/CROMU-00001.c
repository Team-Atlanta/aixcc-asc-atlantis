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

#define MESSAGE_LENGTH  0x20
#define USERNAME_LENGTH 0x10
#define MAX_STDOUT      1024

#define IOCTL_CREATE    0xc00010ff
#define IOCTL_LOGIN     0x1337beef
#define IOCTL_EXIT      0x13370001
#define IOCTL_SEND_MSG  0x13370002
#define IOCTL_READ_MSG  0x13370003
#define IOCTL_LIST_MSG  0x13370004
#define IOCTL_DEL_MSG   0x13370005
#define IOCTL_LOGOUT    0x13370006

/* interface to the device driver */
typedef struct {
  int choice;
  char username[USERNAME_LENGTH];
  char message[MESSAGE_LENGTH];
  int message_id;
  char stdout[MAX_STDOUT];
} req_t;

int g_fd = -1;

int create_user(char *username, int username_size) {
  req_t r = {};

  r.choice = IOCTL_CREATE;
  int copy_bytes = username_size > USERNAME_LENGTH - 1 ? USERNAME_LENGTH - 1 : username_size;
  memcpy(r.username, username, copy_bytes);

  int ret = ioctl(g_fd, IOCTL_CREATE, &r);
  printf("%s", r.stdout);
  return ret;
}

int login(char *username, int username_size) {
  req_t r = {};

  r.choice = IOCTL_LOGIN;
  int copy_bytes = username_size > USERNAME_LENGTH - 1 ? USERNAME_LENGTH - 1 : username_size;
  memcpy(r.username, username, copy_bytes);

  int ret = ioctl(g_fd, IOCTL_LOGIN, &r);
  printf("%s", r.stdout);
  return ret;
}

int service_exit() {
  req_t r = {};

  r.choice = IOCTL_EXIT;

  int ret = ioctl(g_fd, IOCTL_EXIT, &r);
  printf("%s", r.stdout);
  return ret;
}

int send_msg(char *username, int username_size, char *message, int message_size) {
  req_t r = {};

  r.choice = IOCTL_SEND_MSG;
  int copy_bytes = username_size > USERNAME_LENGTH - 1 ? USERNAME_LENGTH - 1 : username_size;
  memcpy(r.username, username, copy_bytes);
  copy_bytes = message_size > MESSAGE_LENGTH - 1 ? MESSAGE_LENGTH - 1 : message_size;
  memcpy(r.message, message, copy_bytes);

  int ret = ioctl(g_fd, IOCTL_SEND_MSG, &r);
  printf("%s", r.stdout);
  return ret;
}

int read_msg(int message_id) {
  req_t r = {};

  r.choice = IOCTL_READ_MSG;
  r.message_id = message_id;

  int ret = ioctl(g_fd, IOCTL_READ_MSG, &r);
  printf("%s", r.stdout);
  return ret;
}

int list_msg() {
  req_t r = {};

  r.choice = IOCTL_LIST_MSG;

  int ret = ioctl(g_fd, IOCTL_LIST_MSG, &r);
  printf("%s", r.stdout);
  return ret;
}

int del_msg(int message_id) {
  req_t r = {};

  r.choice = IOCTL_DEL_MSG;
  r.message_id = message_id;

  int ret = ioctl(g_fd, IOCTL_DEL_MSG, &r);
  printf("%s", r.stdout);
  return ret;
}

int logout() {
  req_t r = {};
  
  r.choice = IOCTL_LOGOUT;

  int ret = ioctl(g_fd, IOCTL_LOGOUT, &r);
  printf("%s", r.stdout);
  return ret;
}

/***
 * Blob begins with a 4 byte command count
 * [4-bytes command count]
 * Currently there are eight commands:
 *  IOCTL_CREATE    - send create command to the target driver
 *                    [4-bytes size][size-bytes username data]
 *  IOCTL_LOGIN     - send login command to the target driver
 *                    [4-bytes size][size-bytes username data]
 *  IOCTL_EXIT      - send exit command to the target driver
 *                    [None]
 *  IOCTL_SEND_MSG  - send send_msg command to the target driver
 *                    [4-bytes username_size][username_size-bytes username data][4-bytes msg_size][msg_size-bytes username data]
 *  IOCTL_READ_MSG  - send read_msg command to the target driver
 *                    [4-bytes msg_id]
 *  IOCTL_LIST_MSG  - send list_msg command to the target driver
 *                    [None]
 *  IOCTL_DEL_MSG   - send del_msg command to the target driver
 *                    [4-bytes msg_id]
 *  IOCTL_LOGOUT    - send logout command to the target driver
 *                    [None]
 *
 * blob_size MUST be a trusted value
 */
int harness( uint8_t *blob, uint32_t blob_size)
{
    int index = 0;
    uint32_t command, command_count = 0;
    uint32_t size = 0;
    uint32_t size2 = 0;
    uint8_t* ptr = NULL;
    int msg_id = 0;

    printf("[INFO] harness blob_size %u \n", blob_size);

    if ( blob == NULL ) {
        return -1;
    }
    if((g_fd = open("/dev/CROMU-00001", O_RDONLY)) < 0) {
      printf("[ERROR] unable to open CROMU-00001 \n");
      return -1;
    }

    if ( blob_size < 4 ) {
        close(g_fd);
        return -1;
    }

    memcpy(&command_count, blob, 4);
    index += 4;

    printf("[INFO] Executing %d commands\n", command_count);
    for ( uint32_t i = 0; i < command_count; i++) {
        if ( blob_size - index < 4 ) {
            printf("[ERROR] ran out of commands\n");
            close(g_fd);
            return -1;
        }

        memcpy(&command, blob + index, 4);
        index += 4;

        switch ( command ) {
          case IOCTL_CREATE:
            if ( blob_size - index < 4 ) {
              printf("[ERROR] create_user error\n");
              close(g_fd);
              return -1;
            }
            memcpy(&size, blob + index, 4);
            index += 4;
            if ( blob_size - index < size ) {
              printf("[ERROR] create_user error\n");
              close(g_fd);
              return -1;
            }
            if (create_user(blob + index, size) < 0) {
              printf("[ERROR] create_user error\n");
              close(g_fd);
              return -1;
            }
            index += size;
            break;
          case IOCTL_LOGIN:
            if ( blob_size - index < 4 ) {
              printf("[ERROR] login error\n");
              close(g_fd);
              return -1;
            }
            memcpy(&size, blob + index, 4);
            index += 4;
            if ( blob_size - index < size ) {
              printf("[ERROR] login error\n");
              close(g_fd);
              return -1;
            }
            if (login(blob + index, size) < 0) {
              printf("[ERROR] login error\n");
              close(g_fd);
              return -1;
            }
            index += size;
            break;
          case IOCTL_EXIT:
            if (service_exit() < 0) {
              printf("[ERROR] exit error\n");
              close(g_fd);
              return -1;
            }
            break;
          case IOCTL_SEND_MSG:
            if ( blob_size - index < 4 ) {
              printf("[ERROR] send_msg error\n");
              close(g_fd);
              return -1;
            }
            memcpy(&size, blob + index, 4);
            index += 4;
            if ( blob_size - index < size ) {
              printf("[ERROR] send_msg error\n");
              close(g_fd);
              return -1;
            }
            ptr = blob + index;
            index += size;
            if ( blob_size - index < 4 ) {
              printf("[ERROR] send_msg error\n");
              close(g_fd);
              return -1;
            }
            memcpy(&size2, blob + index, 4);
            index += 4;
            if ( blob_size - index < size2 ) {
              printf("[ERROR] send_msg error\n");
              close(g_fd);
              return -1;
            }
            if (send_msg(ptr, size, blob + index, size2) < 0) {
              printf("[ERROR] send_msg error\n");
              close(g_fd);
              return -1;
            }
            index += size2;
            break;
          case IOCTL_READ_MSG:
            if ( blob_size - index < 4 ) {
              printf("[ERROR] read_msg error\n");
              close(g_fd);
              return -1;
            }
            memcpy(&msg_id, blob + index, 4);
            index += 4;
            if (read_msg(msg_id) < 0) {
              printf("[ERROR] read_msg error\n");
              close(g_fd);
              return -1;
            }
            break;
          case IOCTL_LIST_MSG:
            if (list_msg() < 0) {
              printf("[ERROR] list_msg error\n");
              close(g_fd);
              return -1;
            }
            break;
          case IOCTL_DEL_MSG:
            if ( blob_size - index < 4 ) {
              printf("[ERROR] del_msg error\n");
              close(g_fd);
              return -1;
            }
            memcpy(&msg_id, blob + index, 4);
            index += 4;
            if (del_msg(msg_id) < 0) {
              printf("[ERROR] del_msg error\n");
              close(g_fd);
              return -1;
            }
            break;
          case IOCTL_LOGOUT:
            if (logout() < 0) {
              printf("[ERROR] logout error\n");
              close(g_fd);
              return -1;
            }
            break;
          default:
            printf("[ERROR] Unknown command: %x\n", command);
            return -1;
        }
    }

    close(g_fd);
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

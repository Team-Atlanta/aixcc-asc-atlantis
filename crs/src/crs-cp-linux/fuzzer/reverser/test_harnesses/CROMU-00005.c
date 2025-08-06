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
  unsigned char *buf;
  int buf_len;

  char stdout[MAX_STDOUT];
} req_t;

void init(int g_fd){
  char buf[20] = {};
  req_t req = {};
  req.buf = buf;
  req.buf_len = sizeof(buf);

  ioctl(g_fd, 0, &req);
  printf("[INFO] stdout: %s \n", req.stdout);
}

/***
 * Blob begins with a 4 byte command count
 * [4-bytes command count]
 * Currently there is a single command:
 *  0   - send next chess move
 *        [4-bytes mov_len][move_len-bytes chess_move data]
 *
 * blob_size MUST be a trusted value
 */
int harness( uint8_t *blob, uint32_t blob_size)
{
    int index = 0;
    uint32_t command, command_count = 0;
    uint32_t size = 0;

    int g_fd = -1;

    printf("[INFO] harness blob_size %u \n", blob_size);

    if ( blob == NULL ) {
        return -1;
    }
    if((g_fd = open("/dev/CROMU-00005", O_RDONLY)) < 0) {
      printf("[ERROR] unable to open CROMU-00005 \n");
      return -1;
    }

    if ( blob_size < 4 ) {
        close(g_fd);
        return -1;
    }

    init(g_fd);

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
          case 0:
            if ( blob_size - index < 4 ) {
              printf("[ERROR] next_chess_move error\n");
              close(g_fd);
              return -1;
            }
            memcpy(&size, blob + index, 4);
            index += 4;
            if ( blob_size - index < size ) {
              printf("[ERROR] decode_wav error. ran out of data \n");
              close(g_fd);
              return -1;
            }

            req_t req = {};
            req.buf = blob+ index;
            req.buf_len = size;
            if (ioctl(g_fd, 0, &req) < 0) {
              printf("[ERROR] next_chess_move ioctl error\n");
              close(g_fd);
              return -1;
            }
            index += size;
            printf("[INFO] stdout: %s \n", req.stdout);
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

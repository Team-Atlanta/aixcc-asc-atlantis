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

#define MAX_STDOUT 1024

typedef struct {
  uint8_t *buf;
  uint32_t buf_len;
  char stdout[MAX_STDOUT];
} req_t;

int g_fd = -1;

int ioctl_CADET_00001( uint8_t *blob, uint32_t blob_size ) {
  req_t req;
  req.buf = blob;
  req.buf_len = blob_size;
  return ioctl(g_fd, 0, &req);
}

/***
 * Blob begins with a 4 byte command count
 * [4-bytes command count]
 * Currently there is a single command:
 *  0 - send ioctl command to the target driver
 *      [4-bytes size][size-bytes data data]
 * blob_size MUST be a trusted value
 */
int harness( uint8_t *blob, uint32_t blob_size)
{
    int index = 0;
    uint32_t command, command_count = 0;
    uint32_t size = 0;

    if ( blob == NULL ) {
        return -1;
    }
    if((g_fd = open("/dev/CADET-00001", O_RDONLY)) < 0) return -1;

    if ( blob_size < 4 ) {
        close(g_fd);
        return -1;
    }

    memcpy(&command_count, blob, 4);
    index += 4;

    printf("[INFO] Executing %d commands\n", command_count);
    for ( uint32_t i = 0; i < command_count; i++) {
        if ( blob_size - index < 4 ) {
            close(g_fd);
            return -1;
        }

        memcpy(&command, blob + index, 4);
        index += 4;

        switch ( command ) {
          case 0:
            memcpy(&size, blob + index, 4);
            index += 4;
            if ( blob_size - index < size ) {
              close(g_fd);
              return -1;
            }
            if (ioctl_CADET_00001(blob + index, size) < 0) {
              printf("[ERROR] ioctl_CADET_00001 error\n");
              close(g_fd);
              return -1;
            }
            index += size;
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
        return 0;
    }

    read(fd, blob, st.st_size);

    close(fd);

    harness(blob, st.st_size);

    return 0;
}

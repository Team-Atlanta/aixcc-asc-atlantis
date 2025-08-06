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

#define MAX_STDOUT    (1048576)

#define IOCTL_BASE 0xdeadbeef
#define IOCTL_ONE IOCTL_BASE + 1
#define IOCTL_TWO IOCTL_BASE + 2
#define IOCTL_THREE IOCTL_BASE + 3
#define IOCTL_FOUR IOCTL_BASE + 4
#define IOCTL_FIVE IOCTL_BASE + 5
#define IOCTL_SIX IOCTL_BASE + 6
#define IOCTL_SEVEN IOCTL_BASE + 7
#define IOCTL_EIGHT IOCTL_BASE + 8
#define IOCTL_NINE IOCTL_BASE + 9
#define IOCTL_TEN IOCTL_BASE + 10

typedef struct {
  unsigned char *buf;
  int buf_len;

  char stdout[MAX_STDOUT];
} req_t;

int g_fd = -1;

int ioctl_send_command(int cmd, char *buf, int buf_len) {
    req_t req;
    int ioctl_res;
    req.buf = buf;
    req.buf_len = buf_len;
    ioctl_res = ioctl(g_fd, cmd, &req);
    printf("[INFO] received: %s\n", req.stdout);
    return ioctl_res;
}

int ioctl_send_command_without_buffer(int cmd) {
    return ioctl_send_command(cmd, NULL, 0);
}

/***
 * Blob begins with a 4 byte command count
 * [4-bytes command count]
 * Currently there are six commands:
 *  1 - do_list command
 *  2 - do_add command
 *  3 - do_count command
 *  4 - do_show command
 *  5 - do_help command
 *  6 - do_quit command
 * blob_size MUST be a trusted value
 */
int harness(uint8_t *blob, uint32_t blob_size)
{
    int index = 0;
    uint32_t command, command_count = 0;
    uint32_t buf_len;
    char *buf;

    printf("[INFO] harness blob_size %u \n", blob_size);

    if (blob == NULL) {
        return -1;        
    }

    if ((g_fd = open("/dev/NRFIN-00001", O_RDONLY)) < 0) {
        printf("[ERROR] unable to open NRFIN-00001\n");
        return -1;
    }

    if (blob_size < 4) {
        printf("[ERROR] blob size error\n");
        goto err;
    }

    memcpy(&command_count, blob, 4);
    index += 4;

    printf("[INFO] Executing %d commands\n", command_count);

    for (uint32_t i = 0; i < command_count; i++) {
        if (blob_size - index < 4) {
            printf("[ERROR] ran out of commands\n");
            goto err;
        }

        memcpy(&command, blob + index, 4);
        index += 4;

        switch (command){
            case IOCTL_ONE:
                printf("[INFO] command: LIST\n");
                if (ioctl_send_command_without_buffer(IOCTL_ONE) < 0) {
                    goto ioctl_err;
                }
                break;
            case IOCTL_TWO:
                printf("[INFO] command: ADD\n");
                if (blob_size - index < 4) {
                    printf("[ERROR] need buf_len\n");
                    goto err;
                }
                memcpy(&buf_len, blob + index, 4);
                index += 4;
                if (blob_size - index < buf_len) {
                    printf("[ERROR] ran out of buf (buf_len: %d; remain blob: %d)\n", buf_len, blob_size-index);
                    goto err;
                }
                buf = malloc(buf_len + 1);
                if (buf == NULL) {
                    printf("[ERROR] malloc error\n");
                    goto err;
                }
                memset(buf, 0, buf_len + 1);
                memcpy(buf, blob + index, buf_len);
                index += buf_len;
                if (ioctl_send_command(IOCTL_TWO, buf, buf_len) < 0) {
                    free(buf);
                    goto ioctl_err;
                }
                free(buf);
                break;        
            case IOCTL_THREE:
                printf("[INFO] command: COUNT\n");
                if (ioctl_send_command_without_buffer(IOCTL_THREE) < 0) {
                    goto ioctl_err;
                }
                break;
            case IOCTL_FOUR:
                printf("[INFO] command: SHOW\n");
                if (blob_size - index < 4) {
                    printf("[ERROR] need buf_len\n");
                    goto err;
                }
                memcpy(&buf_len, blob + index, 4);
                index += 4;
                if (blob_size - index < buf_len) {
                    printf("[ERROR] ran out of buf\n");
                    goto err;
                }
                buf = malloc(buf_len + 1);
                if (buf == NULL) {
                    printf("[ERROR] malloc error\n");
                    goto err;
                }
                memset(buf, 0, buf_len + 1);
                memcpy(buf, blob + index, buf_len);
                index += buf_len;
                if (ioctl_send_command(IOCTL_FOUR, buf, buf_len) < 0) {
                    free(buf);
                    goto ioctl_err;
                }
                free(buf);
                break;  
            case IOCTL_FIVE:
                printf("[INFO] command: HELP\n");
                if (ioctl_send_command_without_buffer(IOCTL_FIVE) < 0) {
                    goto ioctl_err;
                }
                break;
            case IOCTL_SIX:
                printf("[INFO] command: QUIT\n");
                if (ioctl_send_command_without_buffer(IOCTL_SIX) < 0) {
                    goto ioctl_err;
                }
                break;
            default:
                printf("[ERROR] unknown command: %d\n", command);
                goto err;
        }
    }

    close(g_fd);
    return 0;
ioctl_err:
    printf("[ERROR] ioctl error\n");
err:
    close(g_fd);
    return -1;
}


int main(int argc, char *argv[])
{
    char *blob = NULL;
    struct stat st;
    int fd;

    printf("[INFO] main start!\n");

    if (argc < 2) {
        printf("Need file\n");
        return -1;
    }

    if (stat(argv[1], &st) != 0) {
        printf("Failed to stat file\n");
        return -1;
    }

    fd = open(argv[1], O_RDONLY);

    if (fd < 0) {
        printf("[ERROR] failed to open file\n");
        return -1;
    }

    blob = malloc(st.st_size);

    if (blob == NULL) {
        printf("[ERROR] malloc failed\n");
        return 0;
    }

    read(fd, blob, st.st_size);

    close(fd);

    harness(blob, st.st_size);

    return 0;
}
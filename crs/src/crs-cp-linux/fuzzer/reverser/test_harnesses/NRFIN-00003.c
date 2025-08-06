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

#define MAX_STDOUT 1048576
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
    buf[buf_len] = '\n';
    buf[buf_len+1] = '\x00';
    req.buf = buf;
    req.buf_len = buf_len+1;
    ioctl_res = ioctl(g_fd, cmd, &req);
    printf("[INFO] received: %s\n", req.stdout);
    return ioctl_res;
}

/***
 * Blob begins with a 4 byte command count
 * [4-bytes command count]
 * Currently there are ten commands:
 *   1 - do_tip command
 *   2 - do_status command
 *   3 - do_gimme command
 *   4 - do_list command
 *   5 - do_smore command
 *   6 - do_youup command
 *   7 - do_mooch command
 *   8 - do_sup command
 *   9 - do_auth command
 *  10 - quit command
 * blob_size MUST be a trusted value
 */
int harness(uint8_t *blob, uint32_t blob_size)
{
    int index = 0;
    uint32_t command, command_count = 0;
    uint32_t buf_len, buf_header_len;
    char *buf;
    char buf_header[8];

    printf("[INFO] harness blob_size %u \n", blob_size);

    if (blob == NULL) {
        return -1;        
    }

    if ((g_fd = open("/dev/NRFIN-00003", O_RDONLY)) < 0) {
        printf("[ERROR] unable to open NRFIN-00003\n");
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
        memset(buf_header, 0, 8);

        if (blob_size - index < 4) {
            printf("[ERROR] ran out of commands\n");
            goto err;
        }

        memcpy(&command, blob + index, 4);
        index += 4;

        switch (command) {
            case IOCTL_ONE:
                printf("[INFO] command: TIP\n");
                memcpy(buf_header, "TIP ", 4);
                goto with_buffer;
            case IOCTL_THREE:
                printf("[INFO] command: GIMME\n");
                memcpy(buf_header, "GIMME ", 6);
                goto with_buffer;
            case IOCTL_FIVE:
                printf("[INFO] command: SMORE\n");
                memcpy(buf_header, "SMORE ", 6);
                goto with_buffer;
            case IOCTL_SEVEN:
                printf("[INFO] command: MOOCH\n");
                memcpy(buf_header, "MOOCH ", 6);
                goto with_buffer;
            case IOCTL_NINE:
                memcpy(buf_header, "AUTH ", 5);
                printf("[INFO] command: AUTH\n");
with_buffer:
                buf_header_len = strlen(buf_header);
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
                buf = malloc(buf_header_len + buf_len + 2);
                if (buf == NULL) {
                    printf("[ERROR] malloc error\n");
                    goto err;
                }
                memset(buf, 0, buf_header_len + buf_len + 2);
                memcpy(buf, buf_header, buf_header_len);
                memcpy(buf + buf_header_len, blob + index, buf_len);
                index += buf_len;
                if (ioctl_send_command(command, buf, buf_header_len + buf_len) < 0) {
                    free(buf);
                    goto ioctl_err;
                }
                free(buf);
                break;
            case IOCTL_TWO:
                printf("[INFO] command: STATUS\n");
                memcpy(buf_header, "STATUS", 6);
                goto without_buffer;
            case IOCTL_FOUR:
                printf("[INFO] command: LIST\n");
                memcpy(buf_header, "LIST", 4);
                goto without_buffer;
            case IOCTL_SIX:
                printf("[INFO] command: YOUUP\n");
                memcpy(buf_header, "YOUUP", 5);
                goto without_buffer;
            case IOCTL_EIGHT:
                printf("[INFO] command: SUP\n");
                memcpy(buf_header, "SUP", 3);
                goto without_buffer;
            case IOCTL_TEN:
                printf("[INFO] command: QUIT\n");
                memcpy(buf_header, "QUIT", 4);
without_buffer:
                buf_header_len = strlen(buf_header);
                if (ioctl_send_command(command, buf_header, buf_header_len) < 0) {
                    goto ioctl_err;
                }
                break;
            default:
                printf("[ERROR] unknown command: %d\n", command);
                goto err;
                break;
        }
    }

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
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

#define MAX_STDOUT      (1048576)
#define MAX_DATA        (1048576)

#define IOCTL_INIT_STDIN 0x40
#define IOCTL_GET_STDOUT 0x41
#define WORK_WITH_DATA 0x50

#define TOKEN_HELLO "HELLO"
#define TOKEN_AUTH "AUTH"
#define TOKEN_SET "SET"
#define TOKEN_CALL "CALL"
#define TOKEN_BYE "BYE"

typedef struct {
  int cmd;
  unsigned char *buf;
  ssize_t buf_len;
  ssize_t buf_idx;
  ssize_t out_len;
  ssize_t write_slices[2048][2];
  char stdout[MAX_STDOUT];
} req_t;

int g_fd = -1;
char g_token[128];
long g_token_long = 0;

int init_stdin()
{
    req_t req;
    req.cmd = IOCTL_INIT_STDIN;
    printf("[INFO] ioctl:IOCTL_INIT_STDIN\n");
    int ret = ioctl(g_fd, IOCTL_INIT_STDIN, &req);
    return ret;
}

int get_stdout()
{
    req_t req;
    req.cmd = IOCTL_GET_STDOUT;
    printf("[INFO] ioctl:IOCTL_GET_STDOUT\n");
    int ret = ioctl(g_fd, IOCTL_GET_STDOUT, &req);
    return ret;
}

int work_with_data(char *buf, ssize_t buf_len)
{
    if (strncmp(buf, TOKEN_AUTH, strlen(TOKEN_AUTH)) == 0) {
        if (g_token_long == 0) {
            printf("[ERROR] work_with_data error (do HELLO before AUTH)\n");
            return -1;
        } else {
            char *newbuf = realloc(buf, buf_len + 9);
            if (newbuf == NULL) {
                printf("[ERROR] realloc failed\n");
                return -1;
            } else {
                buf = newbuf;
            }
            buf_len += 9;
            snprintf(buf, 15, "AUTH %08lx\n", g_token_long);
        }
    }

    req_t req;
    req.cmd = WORK_WITH_DATA;
    req.buf = buf;
    req.buf_len = buf_len;

    printf("[INFO] ioctl:WORK_WITH_DATA\n");
    printf("[INFO] - write: %s", req.buf);
    int ret = ioctl(g_fd, WORK_WITH_DATA, &req);
    if (ret == 0) {
        printf("[INFO] - read: %s", req.stdout);
        if (strncmp(buf, TOKEN_HELLO, strlen(TOKEN_HELLO)) == 0) {
            memset(g_token, 0, sizeof(g_token));
            memcpy(g_token, &req.stdout[3], strlen(req.stdout) - 4);
            g_token_long = strtol(g_token, NULL, 16);
        } 
    } else {
        printf("[ERROR] work_with_data error (ioctl error)\n");
    }
    return ret;
}

int harness(uint8_t *blob, uint32_t blob_size)
{
    int index = 0;
    uint32_t command, command_count = 0;
    ssize_t buf_len;
    char *buf;

    printf("[INFO] harness blob_size %u \n", blob_size);

    if (blob == NULL) {
        return -1;        
    }

    if ((g_fd = open("/dev/KPRCA-00001", O_RDONLY)) < 0) {
        printf("[ERROR] unable to open KPRCA-00001");
        return -1;
    }

    if (blob_size < 4) {
        close(g_fd);
        return -1;
    }

    memcpy(&command_count, blob, 4);
    index += 4;

    printf("[INFO] Executing %d commands\n", command_count);
    for (uint32_t i = 0; i < command_count; i++) {
        if (blob_size - index < 4) {
            printf("[ERROR] ran out of commands\n");
            close(g_fd);
            return -1;
        }

        memcpy(&command, blob + index, 4);
        index += 4;

        switch (command) {
            case IOCTL_INIT_STDIN:
                if (init_stdin() < 0) {
                    printf("[ERROR] init_stdin error\n");
                    close(g_fd); 
                    return -1;
                }
                break;
            case IOCTL_GET_STDOUT:
                if (get_stdout() < 0) {
                    printf("[ERROR] get_stdout error\n");
                    close(g_fd); 
                    return -1;
                }
                break;
            case WORK_WITH_DATA:
                if (blob_size - index < 4) {
                    printf("[ERROR] work_with_data error (no data)\n");
                    close(g_fd); 
                    return -1;
                }
                memcpy(&buf_len, blob + index, 8);
                index += sizeof(buf_len);
                if (blob_size - index < buf_len) {
                    printf("[ERROR] work_with_data error (lack of buf content)\n");
                    close(g_fd);
                    return -1;
                }
                buf = malloc(buf_len+1);
                memset(buf, 0, buf_len+1);
                memcpy(buf, blob+index, buf_len);
                index += buf_len;
                if (work_with_data(buf, buf_len) < 0) {
                    close(g_fd);
                    free(buf);
                    return -1;
                }
                free(buf);
                break;
            default:
                printf("[ERROR] unknown command: %x\n", command);
                close(g_fd);
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

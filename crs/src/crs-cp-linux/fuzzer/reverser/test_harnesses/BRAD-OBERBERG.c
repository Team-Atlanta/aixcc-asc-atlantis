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

#define CSAW_IOCTL_BASE     0x77617363
#define CSAW_ALLOC_HANDLE   CSAW_IOCTL_BASE+1
#define CSAW_READ_HANDLE    CSAW_IOCTL_BASE+2
#define CSAW_WRITE_HANDLE   CSAW_IOCTL_BASE+3
#define CSAW_GET_CONSUMER   CSAW_IOCTL_BASE+4
#define CSAW_SET_CONSUMER   CSAW_IOCTL_BASE+5
#define CSAW_FREE_HANDLE    CSAW_IOCTL_BASE+6
#define CSAW_GET_STATS	    CSAW_IOCTL_BASE+7

#define BUF_SIZE            0x100

struct alloc_args {
  unsigned long size;
  unsigned long handle;
};

struct free_args {
  unsigned long handle;
};

struct read_args {
  unsigned long handle;
  unsigned long size;
  void *out;
};

struct write_args {
  unsigned long handle;
  unsigned long size;
  void *in;
};

struct consumer_args {
  unsigned long handle;
  unsigned long pid;
  unsigned char offset;
};

struct csaw_stats {
  unsigned long clients;
  unsigned long handles;
  unsigned long bytes_read;
  unsigned long bytes_written;
  char version[40];
};

static unsigned long g_handle;
static unsigned long g_seed;
static unsigned long g_seed_leaked;
static unsigned long g_pid;
static unsigned long g_tainted;

int allocate_ioctl(int fd, unsigned long size){
  struct alloc_args alloc_args = {};
  alloc_args.size = BUF_SIZE;
  if(ioctl(fd, CSAW_ALLOC_HANDLE, &alloc_args) < 0){
    return -1;
  }
  printf("[INFO] Handle: %lx \n", alloc_args.handle);
  g_handle = alloc_args.handle;
  return 0;
}

void free_ioctl(int fd){
  struct free_args free_args = {};
  free_args.handle = g_tainted == 0 ? g_handle : g_pid ^ g_seed;
  ioctl(fd, CSAW_FREE_HANDLE, &free_args);
}

int read_ioctl(int fd){
  char read_buf[BUF_SIZE] = {};
  struct read_args r_args = {};
  r_args.handle = g_tainted == 0 ? g_handle : g_pid ^ g_seed;
  r_args.size = BUF_SIZE;
  r_args.out = read_buf;
  if(ioctl(fd, CSAW_READ_HANDLE, &r_args) < 0){
    return -1;
  }
  printf("[INFO] Read: %s \n", (char*) r_args.out);
  return 0;
}

int write_ioctl(int fd, uint8_t* data, uint32_t size){
  struct write_args w_args = {};
  w_args.handle = g_tainted == 0 ? g_handle : g_pid ^ g_seed;
  w_args.size = size;
  w_args.in = data;
  printf("[+] Write: %s [+] \n", (char*) w_args.in);
  if(ioctl(fd, CSAW_WRITE_HANDLE, &w_args) < 0 ){
    return -1;
  }
  return 0;
}

int get_consumer_ioctl(int fd, unsigned char offset){
  struct consumer_args get_args = {};
  get_args.handle = g_tainted == 0 ? g_handle : g_pid ^ g_seed;
  get_args.offset = offset;
  if(ioctl(fd, CSAW_GET_CONSUMER, &get_args) < 0){
    return -1;
  }
  printf("[+] CSAW_GET_CONSUMER pid: %lx offset: %d [+] \n", get_args.pid, get_args.offset);
  if(offset == 255 && g_seed_leaked == 0){
    g_seed = get_args.pid ^ g_handle;
    g_seed_leaked = 1;
  }
  return 0;
}

int set_consumer_ioctl(int fd, unsigned char offset, uint32_t pid){
  struct consumer_args set_args = {};
  set_args.handle = g_tainted == 0 ? g_handle : g_pid ^ g_seed;
  set_args.pid = pid;
  set_args.offset = offset;
  printf("[+] CSAW_SET_CONSUMER pid: %lx offset: %d [+] \n", set_args.pid, set_args.offset);
  if(offset == 255 && g_seed_leaked == 0){
    printf("[INFO] skip execution. it won't do you any good without leaking seed first \n");
    return 0;
  }
  if(ioctl(fd, CSAW_SET_CONSUMER, &set_args) < 0){
    return -1;
  }
  if(offset == 255){
    g_pid = pid;
    g_tainted = 1;
  }
  return 0;
}

int stats_ioctl(int fd){
  struct csaw_stats csaw_stats = {};
  if(ioctl(fd, CSAW_GET_STATS, &csaw_stats) < 0){
    return -1;
  }
  printf("[+] Clients %ld, Handles %ld, Bytes Read %ld, Bytes Written %ld, Version %s [+] \n", csaw_stats.clients, csaw_stats.handles, csaw_stats.bytes_read, csaw_stats.bytes_written, csaw_stats.version);
  return 0;
}

/***
 * Blob begins with a 4 byte command count
 * [4-bytes command count]
 * Currently there is a single command:
 *  CSAW_READ_HANDLE    - read
 *                        [None]
 *  CSAW_WRITE_HANDLE   - write
 *                        [4-bytes strlen][strlen-bytes string data]
 *  CSAW_GET_CONSUMER   - get consumer
 *                        [1-byte offset]
 *  CSAW_SET_CONSUMER   - set consumer
 *                        [1-byte offset][4-bytes pid]
 *  CSAW_GET_STATS      - get stats
 *                        [None]
 *
 * blob_size MUST be a trusted value
 */
int harness( uint8_t *blob, uint32_t blob_size)
{
  int index = 0;
  uint32_t command, command_count = 0;
  uint32_t size = 0;

  int g_fd = -1;
  unsigned char offset;
  uint32_t pid;

  printf("[INFO] harness blob_size %u \n", blob_size);

  if ( blob == NULL ) {
    return -1;
  }
  if((g_fd = open("/dev/BRAD-OBERBERG", O_RDONLY)) < 0) {
    printf("[ERROR] unable to open BRAD-OBERBERG \n");
    return -1;
  }

  if ( blob_size < 4 ) {
    close(g_fd);
    return -1;
  }

  allocate_ioctl(g_fd, BUF_SIZE);

  memcpy(&command_count, blob, 4);
  index += 4;

  printf("[INFO] Executing %d commands\n", command_count);
  for ( uint32_t i = 0; i < command_count; i++) {
    if ( blob_size - index < 4 ) {
      printf("[ERROR] ran out of commands\n");
      free_ioctl(g_fd);
      close(g_fd);
      return -1;
    }

    memcpy(&command, blob + index, 4);
    index += 4;

    switch ( command ) {
      case CSAW_READ_HANDLE:
        if (read_ioctl(g_fd) < 0) {
          printf("[ERROR] read_ioctl error\n");
          free_ioctl(g_fd);
          close(g_fd);
          return -1;
        }
        break;
      case CSAW_WRITE_HANDLE:
        if ( blob_size - index < 4 ) {
          printf("[ERROR] CSAW_WRITE_HANDLE error\n");
          free_ioctl(g_fd);
          close(g_fd);
          return -1;
        }
        memcpy(&size, blob + index, 4);
        index += 4;
        if ( blob_size - index < size ) {
          printf("[ERROR] CSAW_WRITE_HANDLE error. ran out of data \n");
          free_ioctl(g_fd);
          close(g_fd);
          return -1;
        }
        if (write_ioctl(g_fd, blob + index, size) < 0) {
          printf("[ERROR] write_ioctl error\n");
          free_ioctl(g_fd);
          close(g_fd);
          return -1;
        }
        index += size;
        break;
      case CSAW_GET_CONSUMER:
        if ( blob_size - index < 1 ) {
          printf("[ERROR] CSAW_GET_CONSUMER error\n");
          free_ioctl(g_fd);
          close(g_fd);
          return -1;
        }
        memcpy(&offset, blob + index, 1);
        index += 1;
        if (get_consumer_ioctl(g_fd, offset) < 0) {
          printf("[ERROR] get_consumer_ioctl error\n");
          free_ioctl(g_fd);
          close(g_fd);
          return -1;
        }
        break;
      case CSAW_SET_CONSUMER:
        if ( blob_size - index < 5 ) {
          printf("[ERROR] CSAW_SET_CONSUMER error\n");
          free_ioctl(g_fd);
          close(g_fd);
          return -1;
        }
        memcpy(&offset, blob + index, 1);
        memcpy(&pid, blob + index + 1, 4);
        index += 5;
        if (set_consumer_ioctl(g_fd, offset, pid) < 0) {
          printf("[ERROR] set_consumer_ioctl error\n");
          free_ioctl(g_fd);
          close(g_fd);
          return -1;
        }
        break;
      case CSAW_GET_STATS:
        if (stats_ioctl(g_fd) < 0) {
          printf("[ERROR] stats_ioctl error\n");
          free_ioctl(g_fd);
          close(g_fd);
          return -1;
        }
        break;
      default:
        printf("[ERROR] Unknown command: %x\n", command);
        return -1;
    }
  }

  free_ioctl(g_fd);
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

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <termios.h>
#include <unistd.h>

static volatile sig_atomic_t interrupted = 0;
static char symlink_path_buf[PATH_MAX] = {0};

static void handle_sigint(int signum) {
    (void)signum;
    interrupted = 1;
}

static speed_t baud_to_speed(int baud) {
    switch (baud) {
        case 0: return B0;
        case 50: return B50;
        case 75: return B75;
        case 110: return B110;
        case 134: return B134;
        case 150: return B150;
        case 200: return B200;
        case 300: return B300;
        case 600: return B600;
        case 1200: return B1200;
        case 1800: return B1800;
        case 2400: return B2400;
        case 4800: return B4800;
        case 9600: return B9600;
        case 19200: return B19200;
        case 38400: return B38400;
        case 57600: return B57600;
        case 115200: return B115200;
        case 230400: return B230400;
#ifdef B460800
        case 460800: return B460800;
#endif
#ifdef B500000
        case 500000: return B500000;
#endif
#ifdef B576000
        case 576000: return B576000;
#endif
#ifdef B921600
        case 921600: return B921600;
#endif
        default: return (speed_t)0;
    }
}

static int open_physical_device(const char *device, int baud) {
    int fd = open(device, O_RDONLY | O_NOCTTY);
    if (fd < 0) {
        fprintf(stderr, "Unable to open device '%s': %s\n", device, strerror(errno));
        return -1;
    }

    if (baud > 0) {
        speed_t speed = baud_to_speed(baud);
        if (speed == 0) {
            fprintf(stderr, "Unsupported baud rate: %d\n", baud);
            close(fd);
            return -1;
        }

        struct termios tio;
        if (tcgetattr(fd, &tio) != 0) {
            fprintf(stderr, "tcgetattr failed: %s\n", strerror(errno));
            close(fd);
            return -1;
        }
        cfmakeraw(&tio);
        if (cfsetispeed(&tio, speed) != 0 || cfsetospeed(&tio, speed) != 0) {
            fprintf(stderr, "Unable to set baud rate: %s\n", strerror(errno));
            close(fd);
            return -1;
        }
        if (tcsetattr(fd, TCSANOW, &tio) != 0) {
            fprintf(stderr, "tcsetattr failed: %s\n", strerror(errno));
            close(fd);
            return -1;
        }
    }

    return fd;
}

static int open_pts_device(const char *link_path, char *symlink_path, size_t symlink_len) {
    int master_fd = posix_openpt(O_RDWR | O_NOCTTY);
    if (master_fd < 0) {
        fprintf(stderr, "posix_openpt failed: %s\n", strerror(errno));
        return -1;
    }

    if (grantpt(master_fd) != 0 || unlockpt(master_fd) != 0) {
        fprintf(stderr, "Unable to prepare pty: %s\n", strerror(errno));
        close(master_fd);
        return -1;
    }

    char *slave_name = ptsname(master_fd);
    if (slave_name == NULL) {
        fprintf(stderr, "ptsname failed: %s\n", strerror(errno));
        close(master_fd);
        return -1;
    }

    struct stat st;
    if (lstat(link_path, &st) == 0) {
        fprintf(stderr, "Path already exists: %s\n", link_path);
        close(master_fd);
        return -1;
    }

    if (symlink(slave_name, link_path) != 0) {
        fprintf(stderr, "Failed to create symlink '%s' -> '%s': %s\n", link_path, slave_name, strerror(errno));
        close(master_fd);
        return -1;
    }

    strncpy(symlink_path, link_path, symlink_len - 1);
    symlink_path[symlink_len - 1] = '\0';
    return master_fd;
}

static void cleanup(int fd, const char *symlink_path) {
    if (fd >= 0) {
        close(fd);
    }
    if (symlink_path != NULL && symlink_path[0] != '\0') {
        struct stat st;
        if (lstat(symlink_path, &st) == 0 && S_ISLNK(st.st_mode)) {
            unlink(symlink_path);
        }
    }
}

static void usage(const char *prog) {
    fprintf(stderr, "Usage: %s [--baud N] [--pts] DEVICE\n", prog);
    exit(1);
}

int main(int argc, char **argv) {
    bool use_pts = false;
    int baud = 0;
    const char *device = NULL;

    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--baud") == 0) {
            if (i + 1 >= argc) {
                usage(argv[0]);
            }
            baud = atoi(argv[++i]);
            if (baud <= 0) {
                fprintf(stderr, "Invalid baud rate: %s\n", argv[i]);
                return 1;
            }
        } else if (strcmp(argv[i], "--pts") == 0) {
            use_pts = true;
        } else if (device == NULL) {
            device = argv[i];
        } else {
            usage(argv[0]);
        }
    }

    if (device == NULL) {
        usage(argv[0]);
    }

    int fd = -1;
    if (use_pts) {
        fd = open_pts_device(device, symlink_path_buf, sizeof(symlink_path_buf));
    } else {
        fd = open_physical_device(device, baud);
    }
    if (fd < 0) {
        return 1;
    }

    struct sigaction action;
    memset(&action, 0, sizeof(action));
    action.sa_handler = handle_sigint;
    sigemptyset(&action.sa_mask);
    sigaction(SIGINT, &action, NULL);

    uint8_t buffer[1024];
    while (!interrupted) {
        ssize_t n = read(fd, buffer, sizeof(buffer));
        if (n < 0) {
            if (errno == EINTR) {
                continue;
            }
            fprintf(stderr, "Read error: %s\n", strerror(errno));
            cleanup(fd, symlink_path_buf);
            return 1;
        }
        if (fwrite(buffer, 1, (size_t)n, stdout) != (size_t)n) {
            fprintf(stderr, "Write error: %s\n", strerror(errno));
            cleanup(fd, symlink_path_buf);
            return 1;
        }
        fflush(stdout);
    }

    cleanup(fd, symlink_path_buf);
    return 0;
}

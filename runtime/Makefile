CC ?= gcc
CFLAGS = -Wall -Wextra -O2 -std=c99 -DNDEBUG
AR = ar

ifeq ($(OS),Windows_NT)
    RM = del /Q
    EXT = .lib
else
    RM = rm -f
    EXT = .a
endif

TARGET = libnova_runtime$(EXT)

SRCS = nova_runtime.c
OBJS = $(SRCS:.c=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(AR) rcs $@ $^

%.o: %.c nova_runtime.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	$(RM) $(OBJS) $(TARGET)

.PHONY: all clean

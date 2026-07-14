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
TEST_TARGET = test_runtime

SRCS = nova_runtime.c
OBJS = $(SRCS:.c=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(AR) rcs $@ $^

$(TEST_TARGET): test_runtime.c nova_runtime.h $(TARGET)
	$(CC) $(CFLAGS) -o $@ test_runtime.c -L. -lnova_runtime -lm

%.o: %.c nova_runtime.h
	$(CC) $(CFLAGS) -c $< -o $@

test: $(TEST_TARGET)
	./$(TEST_TARGET)

clean:
	$(RM) $(OBJS) $(TARGET) $(TEST_TARGET)

.PHONY: all clean test

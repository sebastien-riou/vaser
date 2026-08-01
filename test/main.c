

#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>
#include "vaser.h"
void error_handler(uint32_t error_code){
    switch(error_code){
        case VASER_ERROR_BUFFER_TOO_SMALL:
            printf("Error: Buffer too small\n");
            break;
        default:
            printf("Error: Unknown error code %u\n", error_code);
            break;
    }
}
 
#ifndef GRANULARITY
#define GRANULARITY 4
#endif

typedef struct{
    const char*src;
    sz_t remaining;
} reader_ctx_t;

reader_ctx_t g_reader_ctx;

void set_reader_src(const char*src){
    g_reader_ctx.src = src;
    g_reader_ctx.remaining = strlen(src);
}

bool reader_src_is_empty(){
    return g_reader_ctx.remaining == 0;
}

void reader_core(void* dst, sz_t size){
    for(sz_t i = 0; i < size; i++){
        if(g_reader_ctx.remaining < 2){
            printf("ERROR (reader_core): not enough data to read %zu bytes\n", size);
            fflush(stdout);
            exit(1);
        }
        sscanf(g_reader_ctx.src,"%02hhx", &((uint8_t*)dst)[i]);
        g_reader_ctx.src += 2;
        g_reader_ctx.remaining -= 2;
    }
}
void reader(void* dst, sz_t size){
    if(size % GRANULARITY != 0){
        printf("ERROR (reader): size %zu is not a multiple of granularity %u\n", size, GRANULARITY);
        fflush(stdout);
        exit(1);
    }
    reader_core(dst, size);
}

void writer_core(const void* src, sz_t size){
    for(sz_t i = 0; i < size; i++){
        printf("%02x", ((const uint8_t*)src)[i]);
    }
    //printf("\n");
}

void writer(const void* src, sz_t size){
    if(size % GRANULARITY != 0){
        printf("ERROR (writer): size %zu is not a multiple of granularity %u\n", size, GRANULARITY);
        fflush(stdout);
        exit(1);
    }
    writer_core(src, size);
}

#define ENCODE 1
#define DECODE 2

int main(int argc, char** argv){
    vaser_ctx_t ctx;
    ctx.granularity = GRANULARITY;
    ctx.error_handler = error_handler;
    if(argc < 2){
        printf("Usage: %s encode|decode\n", argv[0]);
        return 1;
    }
    int mode = 0;
    if(strcmp(argv[1], "encode") == 0){
        ctx.writer = writer;
        mode = ENCODE;
    } 
    if(strcmp(argv[1], "decode") == 0){
        ctx.reader = reader;
        mode = DECODE;
    }
    if(!mode){
        printf("Usage: %s encode|decode\n", argv[0]);
        return 1;
    }
    vaser_init(&ctx);
    if(mode == ENCODE){
        for(unsigned int i = 2; i < argc; i++){
            //printf("Encode: %s\n", argv[i]);
            const char* arg = argv[i];
            set_reader_src(arg);
            vaser_flags_t flags = DEFAULT;
            if(i + 1 < argc){
                const char* next_arg = argv[i+1];
                //printf("Next next_arg: '%s'\n", next_arg);
                if(0 == strcmp(next_arg, "last")){
                    flags = LAST_IN_LIST;
                } else if(0 == strcmp(next_arg, "next")){
                    flags = LAST_IN_CHUNK;
                } else if(0 == strcmp(next_arg, "fragment")){
                    flags = FRAGMENT;
                }
                if(flags != DEFAULT){
                    i++;
                }
                //printf("Flags: %d\n", flags);
            } else {
                //printf("implicit next\n");
                flags = LAST_IN_CHUNK;
            }
            sz_t read_size;
            if(0 == strcmp(arg, "null")){
                vaser_encode(&ctx, 0, 0, flags);// 0 length value
            } else {
                read_size = strlen(arg) / 2;
                uint8_t buffer[read_size];
                reader_core(buffer, read_size);
                vaser_encode(&ctx, buffer, read_size, flags);
            }
        }
    } else if(mode == DECODE){
        vaser_flags_t flags;
        for(unsigned int i = 2; i < argc; i++){
            //printf("Decode: %s\n", argv[i]);
            const char* arg = argv[i];
            set_reader_src(arg);
            sz_t read_size = strlen(arg) / 2;
            uint8_t buffer[read_size];
            uint8_t*buf = buffer;
            while(!reader_src_is_empty() || !vaser_is_empty(&ctx)){
                vaser_decode(&ctx, buf, &read_size, &flags);
                if (read_size == 0){
                    printf("null");
                } else {
                    writer_core(buf, read_size);
                }
                //printf("Flags: %d\n", flags);
                if(flags == LAST_IN_LIST){
                    printf(" last");
                } else if(flags == LAST_IN_CHUNK){
                    printf(" next");
                } else if(flags == FRAGMENT){
                    printf(" fragment");
                }
                printf(" ");
            }
        }
    }
    printf("\n");
    return 0;
}
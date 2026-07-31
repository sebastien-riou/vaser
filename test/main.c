

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

char*to_decode;
void reader_core(void* dst, sz_t size){
    for(sz_t i = 0; i < size; i++){
        sscanf(to_decode,"%02hhx", &((uint8_t*)dst)[i]);
        to_decode += 2;
    }
}
void reader(void* dst, sz_t size){
    if(size % GRANULARITY != 0){
        printf("Error: size %zu is not a multiple of granularity %u\n", size, GRANULARITY);
        fflush(stdout);
        exit(1);
    }
    reader_core(dst, size);
}

void writer(const void* src, sz_t size){
    if(size % GRANULARITY != 0){
        printf("Error: size %zu is not a multiple of granularity %u\n", size, GRANULARITY);
        fflush(stdout);
        exit(1);
    }
    for(sz_t i = 0; i < size; i++){
        printf("%02x", ((const uint8_t*)src)[i]);
    }
    printf("\n");
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
        to_decode = argv[2];
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
            printf("Encode: %s\n", argv[i]);
            to_decode = argv[i];
            vaser_flags_t flags = DEFAULT;
            if(i + 1 < argc){
                const char* arg = argv[i+1];
                printf("Next arg: '%s'\n", arg);
                if(0 == strcmp(arg, "last")){
                    flags = LAST_IN_LIST;
                } else if(0 == strcmp(arg, "next")){
                    flags = LAST_IN_CHUNK;
                } else if(0 == strcmp(arg, "fragment")){
                    flags = FRAGMENT;
                }
                printf("Flags: %d\n", flags);
                i++;
            } else {
                printf("implicit next\n");
                flags = LAST_IN_CHUNK;
            }
            sz_t read_size = strlen(to_decode) / 2;
            uint8_t buffer[read_size];
            reader_core(buffer, read_size);
            vaser_encode(&ctx, buffer, read_size, flags);
        }
    } else if(mode == DECODE){
        vaser_flags_t flags;
        for(unsigned int i = 2; i < argc; i++){
            printf("Decode: %s\n", argv[i]);
            to_decode = argv[i];
            sz_t read_size = strlen(to_decode) / 2;
            uint8_t buffer[read_size];
            vaser_decode(&ctx, buffer, &read_size, &flags);
            writer(buffer, read_size);
            printf("Flags: %d\n", flags);
        }
    }
    return 0;
}
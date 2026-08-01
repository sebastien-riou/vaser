

#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>
#include "vaser.h"
void error_handler(uint32_t error_code){
    printf("\n\n");
    switch(error_code){
        case VASER_ERROR_BUFFER_TOO_SMALL:
            printf("ERROR: Buffer too small\n");
            break;
        default:
            printf("ERROR: Unknown error code %u\n", error_code);
            break;
    }
    exit(1);
}
 
#ifndef DEFAULT_GRANULARITY
#define DEFAULT_GRANULARITY 1
#endif

unsigned int g_granularity = DEFAULT_GRANULARITY;

typedef struct{
    const char*src;
    sz_t remaining;
} reader_ctx_t;

void set_reader_src(reader_ctx_t*ctx, const char*src){
    ctx->src = src;
    ctx->remaining = strlen(src);
}

bool reader_src_is_empty(reader_ctx_t*ctx){
    return ctx->remaining == 0;
}

void reader_core(reader_ctx_t*ctx, void* dst, sz_t size){
    for(sz_t i = 0; i < size; i++){
        if(ctx->remaining < 2){
            printf("ERROR (reader_core): not enough data to read %zu bytes\n", size);
            fflush(stdout);
            exit(1);
        }
        sscanf(ctx->src,"%02hhx", &((uint8_t*)dst)[i]);
        ctx->src += 2;
        ctx->remaining -= 2;
    }
}
void reader(void* io_ctx, void* dst, sz_t size){
    if(size % g_granularity != 0){
        printf("ERROR (reader): size %zu is not a multiple of granularity %u\n", size, g_granularity);
        fflush(stdout);
        exit(1);
    }
    reader_core(io_ctx, dst, size);
}

void writer_core(void* io_ctx, const void* src, sz_t size){
    for(sz_t i = 0; i < size; i++){
        printf("%02x", ((const uint8_t*)src)[i]);
    }
    //printf("\n");
}

void writer(void* io_ctx, const void* src, sz_t size){
    if(size % g_granularity != 0){
        printf("ERROR (writer): size %zu is not a multiple of granularity %u\n", size, g_granularity);
        fflush(stdout);
        exit(1);
    }
    writer_core(io_ctx, src, size);
}

#define ENCODE 1
#define DECODE 2

int main(int argc, char** argv){
    vaser_ctx_t ctx;
    ctx.error_handler = error_handler;
    reader_ctx_t g_reader_ctx;
    unsigned int granularity = DEFAULT_GRANULARITY;
    int arg_index = 1;

    if(argc >= 3 && strcmp(argv[1], "--granularity") == 0){
        char* endptr = NULL;
        unsigned long value = strtoul(argv[2], &endptr, 10);
        if(*endptr != '\0' || value == 0){
            fprintf(stderr, "Invalid granularity: %s\n", argv[2]);
            return 1;
        }
        granularity = (unsigned int)value;
        arg_index = 3;
    }

    if(arg_index >= argc){
        printf("Usage: %s [--granularity N] encode|decode\n", argv[0]);
        return 1;
    }

    g_granularity = granularity;
    int mode = 0;
    if(strcmp(argv[arg_index], "encode") == 0){
        vaser_init(&ctx, writer, 0, granularity, error_handler);
        mode = ENCODE;
    } 
    if(strcmp(argv[arg_index], "decode") == 0){
        vaser_init(&ctx, reader, &g_reader_ctx, granularity, error_handler);
        mode = DECODE;
    }
    if(!mode){
        printf("Usage: %s [--granularity N] encode|decode\n", argv[0]);
        return 1;
    }
    
    if(mode == ENCODE){
        for(unsigned int i = arg_index + 1; i < argc; i++){
            //printf("Encode: %s\n", argv[i]);
            const char* arg = argv[i];
            set_reader_src(&g_reader_ctx, arg);
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
                reader_core(&g_reader_ctx, buffer, read_size);
                vaser_encode(&ctx, buffer, read_size, flags);
            }
        }
    } else if(mode == DECODE){
        vaser_flags_t flags;
        for(unsigned int i = arg_index + 1; i < argc; i++){
            //printf("Decode: %s\n", argv[i]);
            const char* arg = argv[i];
            set_reader_src(&g_reader_ctx, arg);
            while(!reader_src_is_empty(&g_reader_ctx) || !vaser_is_empty(&ctx)){
                sz_t read_size = vaser_decode_header(&ctx, &flags);
                if (read_size == 0){
                    printf("null");
                } else {
                    uint8_t buffer[read_size];
                    vaser_decode_payload(&ctx, buffer, read_size,flags);
                    writer_core(0, buffer, read_size);
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
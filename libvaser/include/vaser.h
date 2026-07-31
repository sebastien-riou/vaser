#pragma once

#include <stdint.h>
#include <string.h>
typedef uintptr_t sz_t;

#define VASER_ERROR_BUFFER_TOO_SMALL 1
#define VASER_ERROR_INTERNAL 2
#define VASER_ERROR_UNSUPPORTED_LENGTH 3

static unsigned int vlq_encode_bits(void* dst, sz_t* dst_size, const void* src, sz_t src_bit_length){
    sz_t consumed = 0;
    sz_t produced = 0;
    sz_t produced_bytes = 0;
    uint8_t* dst8 = (uint8_t*)dst;
    const uint8_t* src8 = (const uint8_t*)src;
    uint8_t vlq_byte = 0;
    uint8_t src_byte = *src8;
    while(src_bit_length > consumed){
        vlq_byte |= (src_byte & 1) << produced;
        src_byte >>= 1;
        consumed++;
        if(consumed == 8){
            src_byte = *++src8;
            consumed = 0;   
        }
        produced++;
        if(produced == 7){
            produced = 0;
            if(src_bit_length > consumed) vlq_byte |= 0x80;
            if(produced_bytes == *dst_size){
                //not enough space in dst
                return 1;
            }
            dst8[produced_bytes++] = vlq_byte;
            vlq_byte = 0;
        }
    }
    if(produced > 0){
        if(produced_bytes == *dst_size){
            //not enough space in dst
            return 1;
        }
        dst8[produced_bytes++] = vlq_byte;
        vlq_byte = 0;
    }
    *dst_size = produced_bytes;
    return 0;
}

static unsigned int vlq_encode(void* dst, sz_t* dst_size, const void* src, sz_t src_size){
    sz_t src_bit_length = src_size * 8;
    return vlq_encode_bits(dst, dst_size, src, src_bit_length);
}

static unsigned int vlq_decode(void* dst, sz_t* dst_size, const void* src, sz_t* src_size){
    sz_t consumed = 0;
    sz_t produced = 0;
    sz_t produced_bytes = 0;
    uint8_t dst_byte = 0;
    memset(dst, 0, *dst_size);
    while(consumed < *src_size){
        uint8_t vlq_byte = ((const uint8_t*)src)[consumed++];
        for(unsigned int i = 0; i < 7; i++){
            dst_byte |= ((vlq_byte >> i) & 1) << produced;
            produced++;
            if(produced == 8){
                if(produced_bytes == *dst_size){
                    //not enough space in dst
                    return 1;
                }
                ((uint8_t*)dst)[produced_bytes++] = dst_byte;
                dst_byte = 0;
                produced = 0;
            }
        }
        if((vlq_byte & 0x80) == 0) break;
    }
    if(produced > 0){
        if(produced_bytes == *dst_size){
            //not enough space in dst
            return 1;
        }
        ((uint8_t*)dst)[produced_bytes++] = dst_byte;
    }
    *src_size = consumed;
    *dst_size = produced_bytes;
    return 0;
}

static unsigned int sz_bit_length(sz_t value){
    unsigned int length = 0;
    while(value > 0){
        value >>= 1;
        length++;
    }
    return length;
}

static unsigned int vlq_encode_sz(void* dst, sz_t* dst_size, sz_t value){
    sz_t bit_length = sz_bit_length(value);
    return vlq_encode_bits(dst, dst_size, &value, bit_length);
}

static unsigned int vlq_decode_sz(sz_t*dst,const void* src, sz_t* src_size){
    sz_t dst_size = sizeof(sz_t);
    return vlq_decode(dst, &dst_size, src, src_size);
}

typedef void (*vaser_error_handler_t)(uint32_t error_code);
typedef void (*vaser_reader_t)(void* dst, sz_t size);
typedef void (*vaser_writer_t)(const void* src, sz_t size);

typedef struct{
    unsigned int granularity;
    vaser_error_handler_t error_handler;
    union{
        vaser_reader_t reader;
        vaser_writer_t writer;
    };
    uint64_t buffer;
    unsigned int buf_level;
} vaser_ctx_t;

typedef enum {
    DEFAULT = 0,
    FRAGMENT = 1,
    LAST_IN_CHUNK = 2,
    LAST_IN_LIST = 3
} vaser_flags_t;

static void vaser_raise_error(vaser_ctx_t*ctx, uint32_t error_code){
    if(ctx->error_handler){
        ctx->error_handler(error_code);
    }
    while(1){
        //halt
    }
}

static void vaser_init(vaser_ctx_t*ctx){
    ctx->buf_level = 0;
}

static void vaser_write(vaser_ctx_t*ctx, const void* buffer, sz_t buffer_size){
    printf("vaser_write: buffer_size=%zu\n", buffer_size);
    const unsigned int granularity = ctx->granularity;
    uint8_t* dst8 = (uint8_t*)&ctx->buffer;
    if(granularity == 1){
        ctx->writer(buffer, buffer_size);
    } else {
        sz_t level = ctx->buf_level;
        sz_t remaining = buffer_size;
        const uint8_t* src = (const uint8_t*)buffer;
        while(remaining > 0){
            sz_t to_write = granularity - level;
            if(to_write > remaining) to_write = remaining;
            memcpy(dst8 + level, src, to_write);
            remaining -= to_write;
            src += to_write;
            if(level == granularity){
                ctx->writer(&ctx->buffer, granularity);
                level = 0;
            }
        }
        ctx->buf_level = level;
    }
}

static void vaser_encode(vaser_ctx_t*ctx, const void* buffer, sz_t buffer_size, vaser_flags_t flags){
    if(buffer_size > ((sz_t)-1 >> 2)){
        vaser_raise_error(ctx, VASER_ERROR_UNSUPPORTED_LENGTH);
    }
    sz_t tl = (buffer_size << 2) | flags;
    sz_t tmp[2];
    sz_t tmp_size = sizeof(tmp);
    if(vlq_encode_sz(tmp, &tmp_size, tl)){
        vaser_raise_error(ctx, VASER_ERROR_INTERNAL);
    }
    vaser_write(ctx, tmp, tmp_size);
    vaser_write(ctx, buffer, buffer_size);
    if((flags != DEFAULT) && (ctx->buf_level > 0)){
        //pad to granularity with zeros
        memset((uint8_t*)&ctx->buffer + ctx->buf_level, 0, ctx->granularity - ctx->buf_level);
        ctx->writer(&ctx->buffer, ctx->granularity);
        ctx->buf_level = 0;
    }
}

static void vaser_decode(vaser_ctx_t*ctx, void* dst, sz_t*dst_size, vaser_flags_t* flags){
    sz_t tl;
    uint8_t tl_bytes[sizeof(sz_t)];
    sz_t tl_size = 0;
    do{
        ctx->reader(tl_bytes + tl_size, 1);
        tl_size++;
    } while((tl_bytes[tl_size - 1] & 0x80) != 0);
    printf("vaser_decode: tl_size=%zu\n", tl_size);
    printf("vaser_decode: tl_bytes=");
    for(sz_t i = 0; i < tl_size; i++){
        printf("%02x", tl_bytes[i]);
    }
    printf("\n");
    if(vlq_decode_sz(&tl, tl_bytes, &tl_size)){
        vaser_raise_error(ctx, VASER_ERROR_UNSUPPORTED_LENGTH);
    }
    printf("vaser_decode: tl_size=%zu\n", tl_size);
    
    *flags = (vaser_flags_t)(tl & 3);
    sz_t payload_size = tl >> 2;
    printf("vaser_decode: payload_size=%zu\n", payload_size);
    printf("vaser_decode: *dst_size=%zu\n", *dst_size);
    if(payload_size > *dst_size){
        //not enough space in dst
        vaser_raise_error(ctx, VASER_ERROR_BUFFER_TOO_SMALL);
    }
    ctx->reader(dst, payload_size);
    *dst_size = payload_size;
}


/* SPDX-License-Identifier: GPL-3.0-or-later
 * A DSD test file (DSF) for measuring native DSD (ADR-0144, Finding 120):
 * a 1 kHz sine at 0.25 of full scale, faded in and out, through a
 * second-order sigma-delta modulator, LSB first, 4096-byte blocks per
 * channel as the DSF format lays them out.
 *
 *   cc -O2 -o dsfgen dsfgen.c -lm
 *   ./dsfgen out.dsf 64 10     # DSD64, 10 seconds (128, 256 likewise)
 *
 * Check one with ffmpeg: it decodes to exactly 1000.0 Hz (Finding 120).
 */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
static void le32(FILE *f, uint32_t v) { fwrite(&v, 4, 1, f); }
static void le64(FILE *f, uint64_t v) { fwrite(&v, 8, 1, f); }
int main(int argc, char **argv) {
    unsigned mult = argc > 2 ? atoi(argv[2]) : 64;          /* DSD64, 128, 256 */
    double secs = argc > 3 ? atof(argv[3]) : 10.0, amp = 0.25, hz = 1000.0;
    uint32_t fs = 44100u * mult;
    uint64_t n = (uint64_t)(fs * secs);
    uint64_t bytes = (n + 7) / 8, blocks = (bytes + 4095) / 4096, data = blocks * 4096 * 2;
    FILE *f = fopen(argv[1], "wb");
    fwrite("DSD ", 4, 1, f); le64(f, 28); le64(f, 28 + 52 + 12 + data); le64(f, 0);
    fwrite("fmt ", 4, 1, f); le64(f, 52); le32(f, 1); le32(f, 0); le32(f, 2); le32(f, 2);
    le32(f, fs); le32(f, 1); le64(f, n); le32(f, 4096); le32(f, 0);
    fwrite("data", 4, 1, f); le64(f, 12 + data);
    uint8_t *ch[2]; double i1[2] = {0}, i2[2] = {0}, y[2] = {0};
    for (int c = 0; c < 2; c++) ch[c] = calloc(blocks * 4096, 1);
    for (uint64_t k = 0; k < n; k++) {
        double t = (double)k / fs, fade = t < 0.5 ? t / 0.5 : (t > secs - 0.5 ? (secs - t) / 0.5 : 1.0);
        double x = amp * fade * sin(2 * M_PI * hz * t);
        for (int c = 0; c < 2; c++) {
            i1[c] += x - y[c]; i2[c] += i1[c] - y[c];
            y[c] = i2[c] >= 0 ? 1.0 : -1.0;
            if (y[c] > 0) ch[c][k / 8] |= (uint8_t)(1u << (k % 8));   /* LSB first */
        }
    }
    for (uint64_t b = 0; b < blocks; b++)
        for (int c = 0; c < 2; c++) fwrite(ch[c] + b * 4096, 4096, 1, f);
    fclose(f);
    printf("%s: DSD%u, %u Hz, %llu samples per channel\n", argv[1], mult, fs, (unsigned long long)n);
    return 0;
}

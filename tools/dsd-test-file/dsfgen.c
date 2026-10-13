/* SPDX-License-Identifier: GPL-3.0-or-later
 * A DSD test file (DSF) for measuring native DSD (ADR-0144, Finding 120):
 * a sine at 0.25 of full scale per channel, faded in and out, through a
 * second-order sigma-delta modulator, LSB first, 4096-byte blocks per
 * channel as the DSF format lays them out.
 *
 *   cc -O2 -o dsfgen dsfgen.c -lm
 *   ./dsfgen out.dsf 64 10       # DSD64, 10 seconds, stereo (128, 256 likewise)
 *   ./dsfgen out.dsf 64 10 6     # 5.1: a different tone on each channel
 *
 * Channel c plays 1000 Hz on stereo, else 200 + 100 * c Hz (60 Hz on the
 * LFE of 5.1), so a decoded file shows which channel went where. Check one
 * with ffmpeg: a stereo file decodes to exactly 1000.0 Hz (Finding 120).
 */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
static void le32(FILE *f, uint32_t v) { fwrite(&v, 4, 1, f); }
static void le64(FILE *f, uint64_t v) { fwrite(&v, 8, 1, f); }
/* DSF's channel type by channel count: mono, stereo, 3 channels, quad,
 * 4 channels, 5 channels, 5.1. */
static const uint32_t TYPE[] = {0, 1, 2, 3, 4, 6, 7};
int main(int argc, char **argv) {
    unsigned mult = argc > 2 ? atoi(argv[2]) : 64;          /* DSD64, 128, 256 */
    double secs = argc > 3 ? atof(argv[3]) : 10.0, amp = 0.25;
    int nch = argc > 4 ? atoi(argv[4]) : 2;
    if (nch < 1 || nch > 6) { fprintf(stderr, "channels: 1 to 6\n"); return 1; }
    uint32_t fs = 44100u * mult;
    uint64_t n = (uint64_t)(fs * secs);
    uint64_t bytes = (n + 7) / 8, blocks = (bytes + 4095) / 4096, data = blocks * 4096 * (uint64_t)nch;
    double hz[6];
    for (int c = 0; c < nch; c++) hz[c] = nch == 2 ? 1000.0 : (nch == 6 && c == 3 ? 60.0 : 200.0 + 100.0 * c);
    FILE *f = fopen(argv[1], "wb");
    fwrite("DSD ", 4, 1, f); le64(f, 28); le64(f, 28 + 52 + 12 + data); le64(f, 0);
    fwrite("fmt ", 4, 1, f); le64(f, 52); le32(f, 1); le32(f, 0); le32(f, TYPE[nch]); le32(f, nch);
    le32(f, fs); le32(f, 1); le64(f, n); le32(f, 4096); le32(f, 0);
    fwrite("data", 4, 1, f); le64(f, 12 + data);
    uint8_t *ch[6]; double i1[6] = {0}, i2[6] = {0}, y[6] = {0};
    for (int c = 0; c < nch; c++) ch[c] = calloc(blocks * 4096, 1);
    for (uint64_t k = 0; k < n; k++) {
        double t = (double)k / fs, fade = t < 0.5 ? t / 0.5 : (t > secs - 0.5 ? (secs - t) / 0.5 : 1.0);
        for (int c = 0; c < nch; c++) {
            double x = amp * fade * sin(2 * M_PI * hz[c] * t);
            i1[c] += x - y[c]; i2[c] += i1[c] - y[c];
            y[c] = i2[c] >= 0 ? 1.0 : -1.0;
            if (y[c] > 0) ch[c][k / 8] |= (uint8_t)(1u << (k % 8));   /* LSB first */
        }
    }
    for (uint64_t b = 0; b < blocks; b++)
        for (int c = 0; c < nch; c++) fwrite(ch[c] + b * 4096, 4096, 1, f);
    fclose(f);
    printf("%s: DSD%u, %u Hz, %d channel(s), %llu samples per channel\n", argv[1], mult, fs, nch,
           (unsigned long long)n);
    return 0;
}

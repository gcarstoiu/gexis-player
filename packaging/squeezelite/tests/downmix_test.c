/* SPDX-License-Identifier: GPL-3.0-or-later
 * ADR-0145: the fold-down helper the Squeezelite patch adds (downmix.c),
 * tested on its own. Built and run by run-unit-tests.sh, which takes
 * downmix.c and downmix.h out of squeezelite-downmix.patch, so what is
 * tested is what is patched in.
 *
 * Expected values are written out here, not computed by the code under
 * test: the coefficient tables below come from ITU-R BS.775 / ffmpeg's
 * default rematrix, and the literal sample values were computed to 50
 * digits (Python's decimal) - see each one's comment.
 */
#include "downmix.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures, checks;

#define CHECK(cond, ...) do { checks++; if (!(cond)) { failures++; \
	printf("FAIL %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

#define R2 0.70710678118654752440L

/* Un-normalised left/right coefficients per layout, by channel count. */
struct layout { unsigned channels; const char *name; long double l[8], r[8]; };
static const struct layout layouts[] = {
	{ 3, "FL FR FC",                {1, 0, R2},                    {0, 1, R2} },
	{ 4, "FL FR BL BR",             {1, 0, R2, 0},                 {0, 1, 0, R2} },
	{ 5, "FL FR FC BL BR",          {1, 0, R2, R2, 0},             {0, 1, R2, 0, R2} },
	{ 6, "FL FR FC LFE BL BR",      {1, 0, R2, 0, R2, 0},          {0, 1, R2, 0, 0, R2} },
	{ 7, "FL FR FC LFE BC SL SR",   {1, 0, R2, 0, 0.5L, R2, 0},    {0, 1, R2, 0, 0.5L, 0, R2} },
	{ 8, "FL FR FC LFE BL BR SL SR",{1, 0, R2, 0, R2, 0, R2, 0},   {0, 1, R2, 0, 0, R2, 0, R2} },
};

static long double norm_of(const struct layout *L) {
	long double sl = 0, sr = 0;
	for (unsigned c = 0; c < L->channels; c++) { sl += L->l[c]; sr += L->r[c]; }
	return sl > sr ? sl : sr;
}

static int32_t fold1(const struct downmix *dm, const int32_t *frame, unsigned shift, int side) {
	const int32_t *in[8];
	int32_t out[2];
	for (unsigned c = 0; c < dm->channels; c++) in[c] = frame + c;
	downmix_s32(dm, in, dm->channels, shift, 1, out);
	return out[side];
}

static void test_refuses_what_it_should_not_fold(void) {
	struct downmix dm;
	for (unsigned ch = 0; ch <= 2; ch++)
		CHECK(!downmix_init_default(&dm, ch), "%u channels must not be folded (the decoders keep their own path)", ch);
	CHECK(!downmix_init_default(&dm, 9), "9 channels: more than DOWNMIX_MAX_CHANNELS");
	dm_speaker lfe_only[3] = { DM_LFE, DM_LFE, DM_TC };
	CHECK(!downmix_init(&dm, 3, lfe_only), "nothing reaches either side: refused");
}

static void test_coefficients(void) {
	for (size_t i = 0; i < sizeof(layouts) / sizeof(layouts[0]); i++) {
		const struct layout *L = &layouts[i];
		struct downmix dm;
		CHECK(downmix_init_default(&dm, L->channels), "%u channels folded", L->channels);
		CHECK(!strcmp(dm.layout, L->name), "%u channels: layout '%s', expected '%s'", L->channels, dm.layout, L->name);
		long double n = norm_of(L), sl = 0, sr = 0;
		for (unsigned c = 0; c < L->channels; c++) {
			CHECK(fabsl(dm.l[c] - L->l[c] / n) < 1e-15L && fabsl(dm.r[c] - L->r[c] / n) < 1e-15L,
				  "%u channels, channel %u: %.17g/%.17g, expected %.17Lg/%.17Lg",
				  L->channels, c, dm.l[c], dm.r[c], L->l[c] / n, L->r[c] / n);
			sl += dm.l[c]; sr += dm.r[c];
		}
		CHECK(fabsl((sl > sr ? sl : sr) - 1.0L) < 1e-15L, "%u channels: largest sum is full scale", L->channels);
	}
}

static void test_literal_values(void) {
	struct downmix dm;
	int32_t f[8];

	downmix_init_default(&dm, 6);
	/* 5.1, 24-bit FL = 1000000: L = 1e6 * 256 / (1 + sqrt 2) = 106038671.967... */
	memset(f, 0, sizeof f); f[0] = 1000000;
	CHECK(fold1(&dm, f, 8, 0) == 106038672 && fold1(&dm, f, 8, 1) == 0, "5.1 FL: %d %d",
		  fold1(&dm, f, 8, 0), fold1(&dm, f, 8, 1));
	/* 5.1 centre = 1000000: both sides 1e6 * 256 * 0.7071 / 2.4142 = 74980664.016... */
	memset(f, 0, sizeof f); f[2] = 1000000;
	CHECK(fold1(&dm, f, 8, 0) == 74980664 && fold1(&dm, f, 8, 1) == 74980664, "5.1 FC: %d %d",
		  fold1(&dm, f, 8, 0), fold1(&dm, f, 8, 1));
	/* 5.1 LFE alone: silence on both sides */
	memset(f, 0, sizeof f); f[3] = 8388607;
	CHECK(fold1(&dm, f, 8, 0) == 0 && fold1(&dm, f, 8, 1) == 0, "5.1 LFE is left out");
	/* 5.1 BR alone reaches only the right */
	memset(f, 0, sizeof f); f[5] = 1000000;
	CHECK(fold1(&dm, f, 8, 0) == 0 && fold1(&dm, f, 8, 1) == 74980664, "5.1 BR: right only");
	/* 5.1: FL, FC and BL at 24-bit full scale make exactly full scale on the left */
	memset(f, 0, sizeof f); f[0] = f[2] = f[4] = 8388607;
	CHECK(fold1(&dm, f, 8, 0) == 8388607 * 256, "5.1 full left: %d, expected %d", fold1(&dm, f, 8, 0), 8388607 * 256);

	downmix_init_default(&dm, 8);
	/* 7.1 SL = -1000000: L = -1e6 * 256 * 0.7071 / (1 + 3 * 0.7071) = -57994475.433... */
	memset(f, 0, sizeof f); f[6] = -1000000;
	CHECK(fold1(&dm, f, 8, 0) == -57994475 && fold1(&dm, f, 8, 1) == 0, "7.1 SL: %d", fold1(&dm, f, 8, 0));

	downmix_init_default(&dm, 7);
	/* 6.1 BC = 1000000: both 1e6 * 256 * 0.5 / (1 + 0.7071 + 0.5 + 0.7071) = 43922656.065... */
	memset(f, 0, sizeof f); f[4] = 1000000;
	CHECK(fold1(&dm, f, 8, 0) == 43922656 && fold1(&dm, f, 8, 1) == 43922656, "6.1 BC: %d", fold1(&dm, f, 8, 0));

	downmix_init_default(&dm, 3);
	/* 3 channels, 16-bit centre at 32767: 32767 * 65536 * 0.7071 / 1.7071 = 889489706.076... */
	memset(f, 0, sizeof f); f[2] = 32767;
	CHECK(fold1(&dm, f, 16, 0) == 889489706, "3ch FC 16-bit: %d", fold1(&dm, f, 16, 0));
}

static void test_full_scale_never_wraps(void) {
	/* Every channel at the most negative, the most positive, and mixed signs:
	 * the sum stays within 32 bits, keeps its sign, and reaches full scale
	 * exactly on the side whose coefficients sum to one. */
	for (unsigned ch = 3; ch <= 8; ch++) {
		struct downmix dm;
		int32_t f[8];
		downmix_init_default(&dm, ch);
		for (int side = 0; side < 2; side++) {
			const double *k = side ? dm.r : dm.l;
			double sum = 0;
			for (unsigned c = 0; c < ch; c++) sum += k[c];
			for (unsigned c = 0; c < ch; c++) f[c] = INT32_MIN;
			int32_t lo = fold1(&dm, f, 0, side);
			for (unsigned c = 0; c < ch; c++) f[c] = INT32_MAX;
			int32_t hi = fold1(&dm, f, 0, side);
			CHECK(lo <= 0 && hi >= 0, "%u channels side %d: sign kept (%d, %d)", ch, side, lo, hi);
			CHECK(llabs((long long)lo - llrint(INT32_MIN * sum)) <= 1 && llabs((long long)hi - llrint(INT32_MAX * sum)) <= 1,
				  "%u channels side %d: %d %d, expected %.0f %.0f", ch, side, lo, hi, INT32_MIN * sum, INT32_MAX * sum);
			if (fabs(sum - 1.0) < 1e-12) {
				CHECK(lo == INT32_MIN && hi >= INT32_MAX - 1, "%u channels side %d: full scale %d %d", ch, side, lo, hi);
			}
			/* the worst case for the opposite signs: each channel against its coefficient */
			for (unsigned c = 0; c < ch; c++) f[c] = (c & 1) ? INT32_MIN : INT32_MAX;
			long double ref = 0;
			for (unsigned c = 0; c < ch; c++) ref += (long double)k[c] * f[c];
			int32_t mixed = fold1(&dm, f, 0, side);
			CHECK(llabs((long long)mixed - llrintl(ref)) <= 1, "%u channels side %d, mixed signs: %d, expected %.0Lf",
				  ch, side, mixed, ref);
		}
		/* 8-bit, 16-bit, 24-bit full scale through the shift */
		for (unsigned bits = 8; bits <= 24; bits += 8) {
			for (unsigned c = 0; c < ch; c++) f[c] = -(1 << (bits - 1));
			int32_t lo = fold1(&dm, f, 32 - bits, 0);
			CHECK(lo < 0 && lo >= INT32_MIN, "%u channels %u-bit: %d", ch, bits, lo);
		}
	}
}

static void test_random_against_reference(void) {
	/* 100000 frames of random 24-bit audio per layout, against a long double
	 * reference from the tables above: never more than half a step apart
	 * before rounding, so never more than one step after. */
	srand(145);
	for (size_t i = 0; i < sizeof(layouts) / sizeof(layouts[0]); i++) {
		const struct layout *L = &layouts[i];
		struct downmix dm;
		downmix_init_default(&dm, L->channels);
		long double n = norm_of(L);
		int worst = 0;
		for (int t = 0; t < 100000; t++) {
			int32_t f[8];
			for (unsigned c = 0; c < L->channels; c++) f[c] = (rand() % (1 << 24)) - (1 << 23);
			for (int side = 0; side < 2; side++) {
				long double ref = 0;
				for (unsigned c = 0; c < L->channels; c++)
					ref += (side ? L->r[c] : L->l[c]) / n * (long double)f[c] * 256.0L;
				long long d = llabs((long long)fold1(&dm, f, 8, side) - llrintl(ref));
				if (d > worst) worst = (int)d;
			}
		}
		CHECK(worst <= 1, "%u channels: worst difference from the reference %d steps", L->channels, worst);
	}
}

/* Goertzel amplitude of `hz` in a 32-bit stream, as a fraction of full scale. */
static double amplitude(const int32_t *x, size_t n, size_t stride, double hz, double rate) {
	double w = 2 * M_PI * hz / rate, k = 2 * cos(w), s1 = 0, s2 = 0;
	for (size_t i = 0; i < n; i++) { double s = x[i * stride] / 2147483648.0 + k * s1 - s2; s2 = s1; s1 = s; }
	double re = s1 - s2 * cos(w), im = s2 * sin(w);
	return 2 * sqrt(re * re + im * im) / n;
}

static void test_tones_land_where_they_belong(void) {
	/* A different tone on each channel, as Finding 121's files: each must come
	 * out on its side(s) at its coefficient, and the LFE's nowhere. Planar
	 * input (FLAC's) and interleaved (WAV's) give the same samples. */
	const double rate = 48000;
	const size_t n = 48000; /* one second: every tone a whole number of cycles */
	static const double hz[8] = { 200, 300, 400, 60, 500, 600, 700, 800 };
	for (size_t i = 0; i < sizeof(layouts) / sizeof(layouts[0]); i++) {
		const struct layout *L = &layouts[i];
		const unsigned ch = L->channels;
		struct downmix dm;
		downmix_init_default(&dm, ch);
		int32_t *planar = malloc(sizeof(int32_t) * n * ch), *inter = malloc(sizeof(int32_t) * n * ch);
		int32_t *out = malloc(sizeof(int32_t) * n * 2), *out2 = malloc(sizeof(int32_t) * n * 2);
		for (unsigned c = 0; c < ch; c++)
			for (size_t t = 0; t < n; t++)
				planar[c * n + t] = inter[t * ch + c] = (int32_t)lrint(0.5 * 8388607 * sin(2 * M_PI * hz[c] * t / rate));
		const int32_t *pin[8], *iin[8];
		for (unsigned c = 0; c < ch; c++) { pin[c] = planar + c * n; iin[c] = inter + c; }
		downmix_s32(&dm, pin, 1, 8, n, out);
		downmix_s32(&dm, iin, ch, 8, n, out2);
		CHECK(!memcmp(out, out2, sizeof(int32_t) * n * 2), "%u channels: planar and interleaved agree", ch);
		long double norm = norm_of(L);
		for (unsigned c = 0; c < ch; c++) {
			for (int side = 0; side < 2; side++) {
				double got = amplitude(out + side, n, 2, hz[c], rate);
				double want = 0.5 * 8388607 * 256 / 2147483648.0 * (double)((side ? L->r[c] : L->l[c]) / norm);
				CHECK(fabs(got - want) < 1e-6, "%u channels: %.0f Hz on %s at %.6f, expected %.6f",
					  ch, hz[c], side ? "right" : "left", got, want);
			}
		}
		free(planar); free(inter); free(out); free(out2);
	}
}

static void test_wav_mask(void) {
	struct downmix dm;
	/* 5.1 with side surrounds (KSAUDIO_SPEAKER_5POINT1_SURROUND) */
	CHECK(downmix_init_wav_mask(&dm, 6, 0x60F) && !strcmp(dm.layout, "FL FR FC LFE SL SR"), "mask 0x60F: %s", dm.layout);
	CHECK(fabs(dm.l[4] - dm.l[2]) < 1e-15 && dm.r[4] == 0 && dm.l[5] == 0, "side surrounds weigh as back ones");
	CHECK(downmix_init_wav_mask(&dm, 6, 0x3F) && !strcmp(dm.layout, "FL FR FC LFE BL BR"), "mask 0x3F: %s", dm.layout);
	CHECK(downmix_init_wav_mask(&dm, 6, 0) && !strcmp(dm.layout, "FL FR FC LFE BL BR"), "no mask: the default order");
	CHECK(downmix_init_wav_mask(&dm, 6, 0x80000000u | 0x3F) && !strcmp(dm.layout, "FL FR FC LFE BL BR"), "SPEAKER_ALL ignored");
	/* fewer bits than channels: the rest are left out */
	CHECK(downmix_init_wav_mask(&dm, 4, 0x7) && !strcmp(dm.layout, "FL FR FC ?") && dm.l[3] == 0 && dm.r[3] == 0,
		  "mask short of the channels: %s", dm.layout);
	/* FLC/FRC go to their side whole */
	CHECK(downmix_init_wav_mask(&dm, 4, 0xC3) && !strcmp(dm.layout, "FL FR FLC FRC") && dm.l[2] == dm.l[0], "FLC: %s", dm.layout);
}

static void test_dsf_and_dsdiff(void) {
	struct downmix dm;
	CHECK(downmix_init_dsf(&dm, 6, 7) && !strcmp(dm.layout, "FL FR FC LFE BL BR"), "DSF type 7: %s", dm.layout);
	CHECK(downmix_init_dsf(&dm, 5, 6) && !strcmp(dm.layout, "FL FR FC BL BR"), "DSF type 6: %s", dm.layout);
	CHECK(downmix_init_dsf(&dm, 4, 5) && !strcmp(dm.layout, "FL FR FC LFE"), "DSF type 5 (4 channels): %s", dm.layout);
	CHECK(downmix_init_dsf(&dm, 4, 4) && !strcmp(dm.layout, "FL FR BL BR"), "DSF type 4 (quad): %s", dm.layout);
	CHECK(downmix_init_dsf(&dm, 3, 3) && !strcmp(dm.layout, "FL FR FC"), "DSF type 3: %s", dm.layout);
	CHECK(downmix_init_dsf(&dm, 4, 7) && !strcmp(dm.layout, "FL FR BL BR"), "a type that disagrees with the count: default");
	/* DSF type 5's centre at 0.5: 0.5 * 0.7071 / 1.7071 * 0x7fffffff = 444758425.78... */
	downmix_init_dsf(&dm, 4, 5);
	float z[4] = { 0 }, c[4] = { 0.5f };
	const float *in[4] = { z, z, c, z };
	int32_t out[2];
	downmix_float(&dm, in, 1, out);
	CHECK(out[0] == 444758426 && out[1] == 444758426, "float centre: %d %d", out[0], out[1]);
	/* float overload: +-1.5 everywhere clamps instead of wrapping */
	float big[1] = { 1.5f }, neg[1] = { -1.5f };
	const float *ib[4] = { big, big, big, big }, *in2[4] = { neg, neg, neg, neg };
	downmix_float(&dm, ib, 1, out);
	CHECK(out[0] == INT32_MAX && out[1] == INT32_MAX, "float clamps high: %d", out[0]);
	downmix_float(&dm, in2, 1, out);
	CHECK(out[0] == INT32_MIN && out[1] == INT32_MIN, "float clamps low: %d", out[0]);

	const unsigned char *ids[] = { (const unsigned char *)"MLFT", (const unsigned char *)"MRGT",
		(const unsigned char *)"C   ", (const unsigned char *)"LFE ", (const unsigned char *)"LS  ",
		(const unsigned char *)"RS  ", (const unsigned char *)"SLFT", (const unsigned char *)"XXXX" };
	const dm_speaker want[] = { DM_FL, DM_FR, DM_FC, DM_LFE, DM_BL, DM_BR, DM_FL, DM_UNKNOWN };
	for (int i = 0; i < 8; i++)
		CHECK(downmix_dsdiff_speaker(ids[i]) == want[i], "DSDIFF ID %.4s", ids[i]);
}

int main(void) {
	test_refuses_what_it_should_not_fold();
	test_coefficients();
	test_literal_values();
	test_full_scale_never_wraps();
	test_random_against_reference();
	test_tones_land_where_they_belong();
	test_wav_mask();
	test_dsf_and_dsdiff();
	printf("%d checks, %d failed\n", checks, failures);
	return failures ? 1 : 0;
}

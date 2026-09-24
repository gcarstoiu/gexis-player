# A circular meter section must not draw a spectrum section's background:
# PeppyMeter repaints under the needle from that file, so naming the
# spectrum panel puts a blank panel over the dial (Finding 050).
BEGIN { FS = "[ \t]*=[ \t]*" }
{ sub(/\r$/, "") }
/^\[/ { section = $0; sub(/^\[/, "", section); sub(/\]$/, "", section); next }
FILENAME ~ /spectrum\.txt$/ && $1 == "bgr.filename" { spectrum[$2] = section; next }
FILENAME ~ /meters\.txt$/ && $1 == "meter.type" { type[section] = $2; next }
FILENAME ~ /meters\.txt$/ && $1 == "bgr.filename" { bgr[section] = $2; next }
END {
    for (s in bgr)
        if (type[s] == "circular" && bgr[s] in spectrum) {
            printf "ERROR: %s draws %s, which is the background of spectrum section %s\n", s, bgr[s], spectrum[bgr[s]] > "/dev/stderr"
            bad++
        }
    exit (bad ? 1 : 0)
}

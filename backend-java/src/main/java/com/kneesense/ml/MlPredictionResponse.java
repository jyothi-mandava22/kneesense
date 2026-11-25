package com.kneesense.ml;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.math.BigDecimal;
import java.util.Base64;
import java.util.Locale;
import java.util.Objects;

/** Exact success payload returned by the locked Python ML service contract. */
public record MlPredictionResponse(
    @JsonProperty("kl_grade") int klGrade,
    @JsonProperty("confidence") BigDecimal confidence,
    @JsonProperty("heatmap_base64") String heatmapBase64,
    @JsonProperty("clinician_report") String clinicianReport,
    @JsonProperty("patient_report") String patientReport,
    @JsonProperty("source") String source
) {
    private static final byte[] PNG_SIGNATURE = {
        (byte) 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A
    };
    private static final int MAX_HEATMAP_BYTES = 2 * 1024 * 1024;

    public MlPredictionResponse {
        if (klGrade < 0 || klGrade > 4) {
            throw new IllegalArgumentException("ML response contains an invalid KL grade.");
        }
        Objects.requireNonNull(confidence, "ML confidence is required.");
        if (confidence.compareTo(BigDecimal.ZERO) < 0 || confidence.compareTo(BigDecimal.ONE) > 0) {
            throw new IllegalArgumentException("ML response contains an invalid confidence value.");
        }
        if (heatmapBase64 == null || heatmapBase64.isBlank()) {
            throw new IllegalArgumentException("ML response heatmap is missing.");
        }
        byte[] heatmapBytes;
        try {
            heatmapBytes = Base64.getDecoder().decode(heatmapBase64);
        } catch (IllegalArgumentException ex) {
            throw new IllegalArgumentException("ML response heatmap is not valid Base64.", ex);
        }
        if (heatmapBytes.length < PNG_SIGNATURE.length || heatmapBytes.length > MAX_HEATMAP_BYTES) {
            throw new IllegalArgumentException("ML response heatmap has an invalid size.");
        }
        for (int i = 0; i < PNG_SIGNATURE.length; i++) {
            if (heatmapBytes[i] != PNG_SIGNATURE[i]) {
                throw new IllegalArgumentException("ML response heatmap must be a PNG image.");
            }
        }
        if (clinicianReport == null || clinicianReport.isBlank()
            || patientReport == null || patientReport.isBlank()) {
            throw new IllegalArgumentException("ML response reports are required.");
        }
        if (source == null || !(source.toLowerCase(Locale.ROOT).equals("live")
            || source.toLowerCase(Locale.ROOT).equals("cached"))) {
            throw new IllegalArgumentException("ML response source must be live or cached.");
        }
        source = source.toLowerCase(Locale.ROOT);
    }
}

package com.kneesense.api.assessment.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/** Immediate upload response. It intentionally excludes clinicianReport. */
public record AssessmentUploadResponse(
    Long resultId,
    int klGrade,
    BigDecimal confidence,
    String heatmapBase64,
    String patientReport,
    String source,
    LocalDateTime createdAt
) {
}

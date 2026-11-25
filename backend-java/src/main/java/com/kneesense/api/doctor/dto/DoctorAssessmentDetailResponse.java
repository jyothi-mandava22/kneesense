package com.kneesense.api.doctor.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

public record DoctorAssessmentDetailResponse(
    Long resultId,
    Long patientId,
    String patientEmail,
    int klGrade,
    BigDecimal confidence,
    String source,
    LocalDateTime createdAt,
    String clinicianReport
) {
}

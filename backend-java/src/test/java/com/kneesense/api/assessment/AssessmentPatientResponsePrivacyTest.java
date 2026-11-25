package com.kneesense.api.assessment;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.kneesense.api.assessment.dto.AssessmentDetailResponse;
import com.kneesense.api.assessment.dto.AssessmentUploadResponse;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.assertFalse;

class AssessmentPatientResponsePrivacyTest {

    private final ObjectMapper objectMapper = new ObjectMapper().findAndRegisterModules();

    @Test
    void immediatePatientUploadResponseDoesNotContainClinicianReport() throws Exception {
        AssessmentUploadResponse response = new AssessmentUploadResponse(
            10L, 2, new BigDecimal("0.510000"), "aGVhdG1hcA==", "patient text", "cached",
            LocalDateTime.of(2026, 11, 22, 10, 0)
        );

        String json = objectMapper.writeValueAsString(response);

        assertFalse(json.contains("clinicianReport"));
        assertFalse(json.contains("clinician_report"));
    }

    @Test
    void historicalPatientDetailDoesNotContainClinicianReport() throws Exception {
        AssessmentDetailResponse response = new AssessmentDetailResponse(
            10L, 2, new BigDecimal("0.510000"), "cached",
            LocalDateTime.of(2026, 11, 22, 10, 0), "patient text"
        );

        String json = objectMapper.writeValueAsString(response);

        assertFalse(json.contains("clinicianReport"));
        assertFalse(json.contains("clinician_report"));
    }
}

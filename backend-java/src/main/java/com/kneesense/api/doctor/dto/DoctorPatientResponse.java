package com.kneesense.api.doctor.dto;

import java.time.LocalDateTime;

public record DoctorPatientResponse(
    Long patientId,
    String patientEmail,
    LocalDateTime assignedAt
) {
}

package com.kneesense.api.admin.dto;

import java.time.LocalDateTime;

public record AssignmentResponse(
    Long doctorId,
    String doctorEmail,
    Long patientId,
    String patientEmail,
    LocalDateTime assignedAt,
    boolean newlyCreated
) { }

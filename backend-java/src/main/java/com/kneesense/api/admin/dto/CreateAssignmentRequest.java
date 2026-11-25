package com.kneesense.api.admin.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

public record CreateAssignmentRequest(
    @NotNull(message = "Doctor ID is required.") @Positive(message = "Doctor ID must be positive.") Long doctorId,
    @NotNull(message = "Patient ID is required.") @Positive(message = "Patient ID must be positive.") Long patientId
) { }

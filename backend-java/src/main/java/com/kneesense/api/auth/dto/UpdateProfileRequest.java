package com.kneesense.api.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record UpdateProfileRequest(
    @NotBlank(message = "Full name is required.")
    @Size(max = 120, message = "Full name cannot exceed 120 characters.")
    String fullName
) {
}
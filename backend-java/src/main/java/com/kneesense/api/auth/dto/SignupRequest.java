package com.kneesense.api.auth.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

@JsonIgnoreProperties(ignoreUnknown = true)
public record SignupRequest(
    @NotBlank
    @Size(max = 120)
    String fullName,

    @NotBlank
    @Email
    @Size(max = 254)
    String email,

    @NotBlank
    @Size(min = 8, max = 72)
    String password
) {
}
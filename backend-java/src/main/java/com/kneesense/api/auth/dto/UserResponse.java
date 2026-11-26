package com.kneesense.api.auth.dto;

import com.kneesense.domain.Role;

public record UserResponse(
    Long id,
    String fullName,
    String email,
    Role role
) {
}
package com.kneesense.api.admin.dto;

import com.kneesense.domain.Role;

import java.time.LocalDateTime;

public record AdminUserResponse(
    Long id,
    String email,
    Role role,
    LocalDateTime createdAt
) { }

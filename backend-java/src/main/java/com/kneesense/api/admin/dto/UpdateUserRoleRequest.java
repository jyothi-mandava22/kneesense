package com.kneesense.api.admin.dto;

import com.kneesense.domain.Role;
import jakarta.validation.constraints.NotNull;

public record UpdateUserRoleRequest(
    @NotNull(message = "Role is required.") Role role
) { }

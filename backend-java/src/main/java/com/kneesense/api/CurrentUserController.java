package com.kneesense.api;

import com.kneesense.api.auth.dto.UserResponse;
import com.kneesense.security.AppUserPrincipal;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class CurrentUserController {

    @GetMapping("/api/me")
    public UserResponse currentUser(@AuthenticationPrincipal AppUserPrincipal principal) {
        return new UserResponse(principal.getId(), principal.getUsername(), principal.getRole());
    }
}
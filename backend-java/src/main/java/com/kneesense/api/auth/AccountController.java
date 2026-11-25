package com.kneesense.api.auth;

import com.kneesense.security.AppUserPrincipal;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseCookie;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Duration;

@RestController
@RequestMapping("/api/me")
public class AccountController {

    private final AccountService accountService;
    private final String cookieName;
    private final boolean cookieSecure;

    public AccountController(
        AccountService accountService,
        @Value("${app.auth.cookie-name:KNEESENSE_AUTH}") String cookieName,
        @Value("${app.auth.cookie-secure:false}") boolean cookieSecure
    ) {
        this.accountService = accountService;
        this.cookieName = cookieName;
        this.cookieSecure = cookieSecure;
    }

    @DeleteMapping
    public ResponseEntity<Void> deleteMyAccount(
        @AuthenticationPrincipal AppUserPrincipal principal,
        HttpServletResponse response
    ) {
        accountService.deleteAccount(principal.getId());

        ResponseCookie expiredCookie = ResponseCookie.from(cookieName, "")
            .httpOnly(true)
            .secure(cookieSecure)
            .sameSite("Lax")
            .path("/")
            .maxAge(Duration.ZERO)
            .build();

        response.addHeader(HttpHeaders.SET_COOKIE, expiredCookie.toString());

        return ResponseEntity.noContent().build();
    }
}
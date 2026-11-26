package com.kneesense.api.auth;

import com.kneesense.api.auth.dto.CsrfResponse;
import com.kneesense.api.auth.dto.LoginRequest;
import com.kneesense.api.auth.dto.SignupRequest;
import com.kneesense.api.auth.dto.UserResponse;
import com.kneesense.security.AppUserPrincipal;
import com.kneesense.security.JwtService;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseCookie;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;
import java.time.Duration;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;
    private final AuthenticationManager authenticationManager;
    private final JwtService jwtService;
    private final String cookieName;
    private final boolean cookieSecure;

    public AuthController(
        AuthService authService,
        AuthenticationManager authenticationManager,
        JwtService jwtService,
        @Value("${app.auth.cookie-name:KNEESENSE_AUTH}") String cookieName,
        @Value("${app.auth.cookie-secure:false}") boolean cookieSecure
    ) {
        this.authService = authService;
        this.authenticationManager = authenticationManager;
        this.jwtService = jwtService;
        this.cookieName = cookieName;
        this.cookieSecure = cookieSecure;
    }

    @PostMapping("/signup")
    public ResponseEntity<UserResponse> signup(@Valid @RequestBody SignupRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(authService.signup(request));
    }

    @PostMapping("/login")
    public ResponseEntity<UserResponse> login(
        @Valid @RequestBody LoginRequest request,
        HttpServletResponse response
    ) {
        if (request.password().getBytes(StandardCharsets.UTF_8).length > 72) {
            throw new InvalidCredentialsException();
        }
        Authentication authentication;
        try {
            authentication = authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(
                    AuthService.normalizeEmail(request.email()),
                    request.password()
                )
            );
        } catch (AuthenticationException ex) {
            throw new InvalidCredentialsException();
        }

        AppUserPrincipal principal = (AppUserPrincipal) authentication.getPrincipal();
        String token = jwtService.createToken(principal.getUsername());
        ResponseCookie cookie = ResponseCookie.from(cookieName, token)
            .httpOnly(true)
            .secure(cookieSecure)
            .sameSite("Lax")
            .path("/")
            .maxAge(jwtService.getTokenLifetime())
            .build();
        response.addHeader(HttpHeaders.SET_COOKIE, cookie.toString());

        return ResponseEntity.ok(new UserResponse(
            principal.getId(),
            principal.getFullName(),
            principal.getUsername(),
            principal.getRole()
        ));
    }

    @GetMapping("/csrf")
    public CsrfResponse csrf(CsrfToken csrfToken) {
        return new CsrfResponse(csrfToken.getHeaderName(), "XSRF-TOKEN");
    }

    @PostMapping("/logout")
    public ResponseEntity<Void> logout(HttpServletResponse response) {
        ResponseCookie cookie = ResponseCookie.from(cookieName, "")
            .httpOnly(true)
            .secure(cookieSecure)
            .sameSite("Lax")
            .path("/")
            .maxAge(Duration.ZERO)
            .build();
        response.addHeader(HttpHeaders.SET_COOKIE, cookie.toString());
        return ResponseEntity.noContent().build();
    }
}

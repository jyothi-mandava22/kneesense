package com.kneesense.api.auth;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Map;

@Component
public class LoginAttemptRateLimitFilter extends OncePerRequestFilter {

    private final LoginAttemptRateLimiter rateLimiter;
    private final ObjectMapper objectMapper;

    public LoginAttemptRateLimitFilter(
        LoginAttemptRateLimiter rateLimiter,
        ObjectMapper objectMapper
    ) {
        this.rateLimiter = rateLimiter;
        this.objectMapper = objectMapper;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getServletPath();

        if (path == null || path.isBlank()) {
            String requestUri = request.getRequestURI();
            String contextPath = request.getContextPath();
            path = requestUri != null && contextPath != null && requestUri.startsWith(contextPath)
                ? requestUri.substring(contextPath.length())
                : requestUri;
        }

        return !"POST".equalsIgnoreCase(request.getMethod())
            || !"/api/auth/login".equals(path);
    }

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {

        String clientIp = request.getRemoteAddr();

        if (!rateLimiter.allowAttempt(clientIp)) {
            response.setStatus(org.springframework.http.HttpStatus.TOO_MANY_REQUESTS.value());
            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
            objectMapper.writeValue(
                response.getOutputStream(),
                Map.of(
                    "error", "rate_limited",
                    "message", "Too many login attempts. Please try again shortly."
                )
            );
            return;
        }

        filterChain.doFilter(request, response);
    }
}
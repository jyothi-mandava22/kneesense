package com.kneesense.api.auth;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LoginAttemptRateLimitFilterTest {

    @Test
    void returns429AfterLoginAttemptLimitIsExhausted() throws Exception {
        LoginAttemptRateLimiter limiter =
            new LoginAttemptRateLimiter(1, Duration.ofMinutes(1));
        LoginAttemptRateLimitFilter filter =
            new LoginAttemptRateLimitFilter(limiter, new ObjectMapper());

        MockHttpServletRequest firstRequest = loginRequest();
        MockHttpServletResponse firstResponse = new MockHttpServletResponse();
        MockFilterChain firstChain = new MockFilterChain();

        filter.doFilter(firstRequest, firstResponse, firstChain);

        assertNotNull(firstChain.getRequest());
        assertEquals(200, firstResponse.getStatus());

        MockHttpServletRequest secondRequest = loginRequest();
        MockHttpServletResponse secondResponse = new MockHttpServletResponse();
        MockFilterChain secondChain = new MockFilterChain();

        filter.doFilter(secondRequest, secondResponse, secondChain);

        assertEquals(429, secondResponse.getStatus());
        assertEquals("application/json", secondResponse.getContentType());
        assertTrue(secondResponse.getContentAsString().contains("rate_limited"));
        assertTrue(secondChain.getRequest() == null);
    }

    @Test
    void doesNotLimitOtherEndpoints() throws Exception {
        LoginAttemptRateLimiter limiter =
            new LoginAttemptRateLimiter(1, Duration.ofMinutes(1));
        LoginAttemptRateLimitFilter filter =
            new LoginAttemptRateLimitFilter(limiter, new ObjectMapper());

        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setMethod("POST");
        request.setServletPath("/api/auth/signup");
        request.setRemoteAddr("192.0.2.10");

        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain chain = new MockFilterChain();

        filter.doFilter(request, response, chain);

        assertNotNull(chain.getRequest());
        assertEquals(200, response.getStatus());
    }

    private MockHttpServletRequest loginRequest() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setMethod("POST");
        request.setServletPath("/api/auth/login");
        request.setRemoteAddr("192.0.2.10");
        return request;
    }
}
package com.kneesense.api.auth;

import org.junit.jupiter.api.Test;
import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LoginAttemptRateLimiterTest {

    @Test
    void blocksAttemptsAfterConfiguredCapacity() {
        LoginAttemptRateLimiter limiter =
            new LoginAttemptRateLimiter(2, Duration.ofMinutes(1));

        assertTrue(limiter.allowAttempt("192.0.2.10"));
        assertTrue(limiter.allowAttempt("192.0.2.10"));
        assertFalse(limiter.allowAttempt("192.0.2.10"));
    }

    @Test
    void givesEachIpAnIndependentAllowance() {
        LoginAttemptRateLimiter limiter =
            new LoginAttemptRateLimiter(1, Duration.ofMinutes(1));

        assertTrue(limiter.allowAttempt("192.0.2.10"));
        assertFalse(limiter.allowAttempt("192.0.2.10"));
        assertTrue(limiter.allowAttempt("192.0.2.20"));
    }

    @Test
    void rejectsBlankOrMissingIp() {
        LoginAttemptRateLimiter limiter =
            new LoginAttemptRateLimiter(2, Duration.ofMinutes(1));

        assertThrows(IllegalArgumentException.class,
            () -> limiter.allowAttempt(null));

        assertThrows(IllegalArgumentException.class,
            () -> limiter.allowAttempt(" "));
    }
}
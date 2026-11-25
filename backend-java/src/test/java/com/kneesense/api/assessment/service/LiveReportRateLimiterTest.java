package com.kneesense.api.assessment.service;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LiveReportRateLimiterTest {

    @Test
    void exhaustedUserAllowanceForcesCachedReports() {
        LiveReportRateLimiter limiter =
            new LiveReportRateLimiter(2, Duration.ofDays(1));

        assertFalse(limiter.shouldForceCachedReports(101L));
        assertFalse(limiter.shouldForceCachedReports(101L));
        assertTrue(limiter.shouldForceCachedReports(101L));
    }

    @Test
    void eachUserHasAnIndependentAllowance() {
        LiveReportRateLimiter limiter =
            new LiveReportRateLimiter(1, Duration.ofDays(1));

        assertFalse(limiter.shouldForceCachedReports(101L));
        assertTrue(limiter.shouldForceCachedReports(101L));

        assertFalse(limiter.shouldForceCachedReports(202L));
    }

    @Test
    void rejectsInvalidUserIds() {
        LiveReportRateLimiter limiter =
            new LiveReportRateLimiter(2, Duration.ofDays(1));

        assertThrows(IllegalArgumentException.class,
            () -> limiter.shouldForceCachedReports(null));

        assertThrows(IllegalArgumentException.class,
            () -> limiter.shouldForceCachedReports(0L));
    }
}
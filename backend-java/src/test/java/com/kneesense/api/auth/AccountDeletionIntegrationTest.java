package com.kneesense.api.auth;

import com.kneesense.domain.Role;
import com.kneesense.domain.User;
import com.kneesense.repository.UserRepository;
import jakarta.servlet.http.Cookie;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@Transactional
class AccountDeletionIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Value("${app.auth.cookie-name:KNEESENSE_AUTH}")
    private String cookieName;

    @Test
    void deletingPatientRemovesOnlyTheirDataAndInvalidatesOldCookie() throws Exception {
        String email = "delete-test-" + UUID.randomUUID() + "@example.com";
        String password = "TestPassword123";

        User patient = userRepository.saveAndFlush(
            new User(email, passwordEncoder.encode(password), Role.PATIENT)
        );
        User doctor = userRepository.saveAndFlush(
            new User("doctor-" + UUID.randomUUID() + "@example.com",
                passwordEncoder.encode(password), Role.DOCTOR)
        );
        User otherPatient = userRepository.saveAndFlush(
            new User("other-" + UUID.randomUUID() + "@example.com",
                passwordEncoder.encode(password), Role.PATIENT)
        );

        Long patientId = patient.getId();
        Long doctorId = doctor.getId();
        Long otherPatientId = otherPatient.getId();

        jdbcTemplate.update(
            "INSERT INTO doctor_patient (doctor_id, patient_id) VALUES (?, ?)",
            doctorId, patientId
        );
        jdbcTemplate.update(
            "INSERT INTO doctor_patient (doctor_id, patient_id) VALUES (?, ?)",
            doctorId, otherPatientId
        );

        jdbcTemplate.update(
            "INSERT INTO uploads (user_id, content_hash) VALUES (?, ?)",
            patientId, "a".repeat(64)
        );

        Long uploadId = jdbcTemplate.queryForObject(
            "SELECT id FROM uploads WHERE user_id = ?",
            Long.class, patientId
        );

        jdbcTemplate.update(
            "INSERT INTO results (upload_id, kl_grade, confidence, source) " +
                "VALUES (?, 2, 0.750000, 'cached')",
            uploadId
        );

        Long resultId = jdbcTemplate.queryForObject(
            "SELECT id FROM results WHERE upload_id = ?",
            Long.class, uploadId
        );

        jdbcTemplate.update(
            "INSERT INTO reports (result_id, clinician_text, patient_text) " +
                "VALUES (?, 'Clinician test report', 'Patient test report')",
            resultId
        );

        // Authenticate through the real login endpoint.
        MvcResult loginResult = mockMvc.perform(post("/api/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                        "email": "%s",
                        "password": "%s"
                    }
                    """.formatted(email, password)))
            .andExpect(status().isOk())
            .andReturn();

        var setCookies = loginResult.getResponse().getHeaders("Set-Cookie");

        String authSetCookie = setCookies.stream()
       .filter(value -> value.startsWith(cookieName + "="))
       .findFirst()
       .orElse(null);

assertNotNull(authSetCookie, "Login should issue an authentication cookie.");

Matcher matcher = Pattern.compile(
    "^" + Pattern.quote(cookieName) + "=([^;]+)"
).matcher(authSetCookie);

assertTrue(matcher.find(), "Authentication cookie should be present.");

Cookie oldCookie = new Cookie(cookieName, matcher.group(1));

        // Verify the old cookie is initially valid.
        mockMvc.perform(get("/api/me").cookie(oldCookie))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.email").value(email));

        // Delete the authenticated account.
        mockMvc.perform(delete("/api/me")
                .cookie(oldCookie)
                .with(csrf()))
            .andExpect(status().isNoContent())
            .andExpect(header().string("Set-Cookie",
                org.hamcrest.Matchers.containsString("Max-Age=0")));

        // Verify the account and all patient-owned records were deleted.
        assertFalse(userRepository.existsById(patientId));

        assertEquals(0, jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM doctor_patient WHERE patient_id = ?",
            Integer.class, patientId
        ));

        assertEquals(0, jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM uploads WHERE user_id = ?",
            Integer.class, patientId
        ));

        assertEquals(0, jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM results WHERE id = ?",
            Integer.class, resultId
        ));

        assertEquals(0, jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM reports WHERE result_id = ?",
            Integer.class, resultId
        ));

        // Other users and their assignment must remain intact.
        assertTrue(userRepository.existsById(doctorId));
        assertTrue(userRepository.existsById(otherPatientId));

        assertEquals(1, jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM doctor_patient WHERE doctor_id = ? AND patient_id = ?",
            Integer.class, doctorId, otherPatientId
        ));

        // The old JWT must no longer authenticate.
        mockMvc.perform(get("/api/me").cookie(oldCookie))
            .andExpect(status().isUnauthorized());
    }
}
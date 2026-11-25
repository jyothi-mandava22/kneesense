package com.kneesense.bootstrap;

import com.kneesense.api.auth.AuthService;
import com.kneesense.domain.Role;
import com.kneesense.domain.User;
import com.kneesense.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;

/** Creates the initial administrator exactly once from environment variables. */
@Component
public class AdminBootstrapRunner implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(AdminBootstrapRunner.class);

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final String adminEmail;
    private final String adminPassword;

    public AdminBootstrapRunner(
        UserRepository userRepository,
        PasswordEncoder passwordEncoder,
        @Value("${app.admin.email:}") String adminEmail,
        @Value("${app.admin.password:}") String adminPassword
    ) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.adminEmail = adminEmail == null ? "" : adminEmail.trim();
        this.adminPassword = adminPassword == null ? "" : adminPassword;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        boolean hasEmail = !adminEmail.isBlank();
        boolean hasPassword = !adminPassword.isBlank();

        if (!hasEmail && !hasPassword) {
            log.warn("Admin bootstrap skipped: ADMIN_EMAIL and ADMIN_PASSWORD are not configured.");
            return;
        }
        if (!hasEmail || !hasPassword) {
            throw new IllegalStateException("Both ADMIN_EMAIL and ADMIN_PASSWORD must be configured together.");
        }

        String normalizedEmail = AuthService.normalizeEmail(adminEmail);
        if (normalizedEmail.length() > 254 || !normalizedEmail.matches("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$")) {
            throw new IllegalStateException("ADMIN_EMAIL must be a valid email address no longer than 254 characters.");
        }

        int passwordBytes = adminPassword.getBytes(StandardCharsets.UTF_8).length;
        if (passwordBytes < 12 || passwordBytes > 72) {
            throw new IllegalStateException("ADMIN_PASSWORD must be at least 12 and no more than 72 UTF-8 bytes.");
        }

        userRepository.findByEmailIgnoreCase(normalizedEmail).ifPresentOrElse(existing -> {
            if (existing.getRole() != Role.ADMIN) {
                throw new IllegalStateException(
                    "ADMIN_EMAIL already belongs to a non-admin account. Choose a different email; the account was not promoted."
                );
            }
            log.info("Configured administrator already exists; its password was left unchanged.");
        }, () -> {
            userRepository.save(new User(
                normalizedEmail,
                passwordEncoder.encode(adminPassword),
                Role.ADMIN
            ));
            log.info("Initial administrator account created from environment configuration.");
        });
    }
}

package com.kneesense.api.auth;

import com.kneesense.api.auth.dto.SignupRequest;
import com.kneesense.api.auth.dto.UserResponse;
import com.kneesense.domain.Role;
import com.kneesense.domain.User;
import com.kneesense.repository.UserRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.util.Locale;

@Service
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public AuthService(UserRepository userRepository, PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
    }

    @Transactional
    public UserResponse signup(SignupRequest request) {
        String fullName = request.fullName().trim().replaceAll("\\s+", " ");
        String email = normalizeEmail(request.email());

        if (request.password().getBytes(StandardCharsets.UTF_8).length > 72) {
            throw new PasswordTooLongException();
        }

        if (userRepository.existsByEmailIgnoreCase(email)) {
            throw new EmailAlreadyRegisteredException();
        }

        // Role is never accepted from the request. Public registration always creates PATIENT.
        User saved = userRepository.save(new User(
            email,
            fullName,
            passwordEncoder.encode(request.password()),
            Role.PATIENT
        ));

        return new UserResponse(
            saved.getId(),
            saved.getFullName(),
            saved.getEmail(),
            saved.getRole()
        );
    }

    public static String normalizeEmail(String email) {
        return email.trim().toLowerCase(Locale.ROOT);
    }
}
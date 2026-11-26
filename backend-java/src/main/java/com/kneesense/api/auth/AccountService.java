package com.kneesense.api.auth;

import com.kneesense.domain.User;
import com.kneesense.repository.UserRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class AccountService {

    private final UserRepository userRepository;

    public AccountService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    /**
     * Updates the authenticated user's full name.
     * Does not modify email, password or account role.
     */
    @Transactional
    public User updateFullName(Long userId, String fullName) {
        if (userId == null || userId < 1) {
            throw new IllegalArgumentException("A valid user ID is required.");
        }

        String normalizedName = fullName.trim().replaceAll("\\s+", " ");

        User user = userRepository.findById(userId)
            .orElseThrow(() -> new ResponseStatusException(
                HttpStatus.NOT_FOUND,
                "User account not found."
            ));

        user.setFullName(normalizedName);

        return userRepository.save(user);
    }

    /**
     * Deletes the authenticated user's account.
     * MySQL ON DELETE CASCADE removes assignments, uploads,
     * assessment results and reports belonging to this user.
     */
    @Transactional
    public void deleteAccount(Long userId) {
        if (userId == null || userId < 1) {
            throw new IllegalArgumentException("A valid user ID is required.");
        }

        userRepository.deleteById(userId);
    }
}
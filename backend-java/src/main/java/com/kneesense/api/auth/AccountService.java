package com.kneesense.api.auth;

import com.kneesense.repository.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AccountService {

    private final UserRepository userRepository;

    public AccountService(UserRepository userRepository) {
        this.userRepository = userRepository;
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
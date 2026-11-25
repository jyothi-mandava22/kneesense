package com.kneesense.repository;

import com.kneesense.domain.User;
import com.kneesense.domain.Role;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Long> {

    Optional<User> findByEmailIgnoreCase(String email);

    boolean existsByEmailIgnoreCase(String email);

    List<User> findAllByOrderByEmailAsc();

    List<User> findByRoleOrderByEmailAsc(Role role);
}

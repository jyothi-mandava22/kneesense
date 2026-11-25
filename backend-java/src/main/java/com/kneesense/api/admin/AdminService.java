package com.kneesense.api.admin;

import com.kneesense.api.admin.dto.AdminUserResponse;
import com.kneesense.api.admin.dto.AssignmentResponse;
import com.kneesense.domain.DoctorPatient;
import com.kneesense.domain.DoctorPatientId;
import com.kneesense.domain.Role;
import com.kneesense.domain.User;
import com.kneesense.repository.DoctorPatientRepository;
import com.kneesense.repository.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class AdminService {

    private final UserRepository userRepository;
    private final DoctorPatientRepository doctorPatientRepository;

    public AdminService(UserRepository userRepository, DoctorPatientRepository doctorPatientRepository) {
        this.userRepository = userRepository;
        this.doctorPatientRepository = doctorPatientRepository;
    }

    @Transactional(readOnly = true)
    public List<AdminUserResponse> listUsers(Role role) {
        List<User> users = role == null
            ? userRepository.findAllByOrderByEmailAsc()
            : userRepository.findByRoleOrderByEmailAsc(role);
        return users.stream().map(AdminService::toUserResponse).toList();
    }

    @Transactional
    public AdminUserResponse updateRole(Long userId, Role requestedRole) {
        if (requestedRole == null || requestedRole == Role.ADMIN) {
            throw new InvalidAdminOperationException("Only PATIENT and DOCTOR roles can be assigned through this endpoint.");
        }

        User user = userRepository.findById(userId)
            .orElseThrow(() -> new AdminResourceNotFoundException("User not found."));
        if (user.getRole() == Role.ADMIN) {
            throw new InvalidAdminOperationException("Administrator accounts cannot be changed through this endpoint.");
        }

        user.setRole(requestedRole);
        return toUserResponse(user);
    }

    @Transactional(readOnly = true)
    public List<AssignmentResponse> listAssignments() {
        return doctorPatientRepository.findAll().stream()
            .map(assignment -> toAssignmentResponse(assignment, false))
            .toList();
    }

    @Transactional
    public AssignmentResponse assignPatient(Long doctorId, Long patientId) {
        if (doctorId.equals(patientId)) {
            throw new InvalidAdminOperationException("A user cannot be assigned to themselves as doctor and patient.");
        }

        User doctor = userRepository.findById(doctorId)
            .orElseThrow(() -> new AdminResourceNotFoundException("Doctor account not found."));
        User patient = userRepository.findById(patientId)
            .orElseThrow(() -> new AdminResourceNotFoundException("Patient account not found."));

        if (doctor.getRole() != Role.DOCTOR) {
            throw new InvalidAdminOperationException("The selected doctor account must have the DOCTOR role.");
        }
        if (patient.getRole() != Role.PATIENT) {
            throw new InvalidAdminOperationException("The selected patient account must have the PATIENT role.");
        }

        DoctorPatientId id = new DoctorPatientId(doctorId, patientId);
        if (doctorPatientRepository.existsById(id)) {
            DoctorPatient existing = doctorPatientRepository.findById(id).orElseThrow();
            return toAssignmentResponse(existing, false);
        }

        DoctorPatient saved = doctorPatientRepository.saveAndFlush(new DoctorPatient(doctor, patient));
        return toAssignmentResponse(saved, true);
    }

    @Transactional
    public void removeAssignment(Long doctorId, Long patientId) {
        doctorPatientRepository.deleteById(new DoctorPatientId(doctorId, patientId));
    }

    private static AdminUserResponse toUserResponse(User user) {
        return new AdminUserResponse(user.getId(), user.getEmail(), user.getRole(), user.getCreatedAt());
    }

    private static AssignmentResponse toAssignmentResponse(DoctorPatient assignment, boolean newlyCreated) {
        return new AssignmentResponse(
            assignment.getDoctor().getId(),
            assignment.getDoctor().getEmail(),
            assignment.getPatient().getId(),
            assignment.getPatient().getEmail(),
            assignment.getAssignedAt(),
            newlyCreated
        );
    }
}

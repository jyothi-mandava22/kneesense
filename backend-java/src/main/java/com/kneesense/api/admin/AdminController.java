package com.kneesense.api.admin;

import com.kneesense.api.admin.dto.AdminUserResponse;
import com.kneesense.api.admin.dto.AssignmentResponse;
import com.kneesense.api.admin.dto.CreateAssignmentRequest;
import com.kneesense.api.admin.dto.UpdateUserRoleRequest;
import com.kneesense.domain.Role;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/admin")
public class AdminController {

    private final AdminService adminService;

    public AdminController(AdminService adminService) {
        this.adminService = adminService;
    }

    @GetMapping("/users")
    public List<AdminUserResponse> listUsers(@RequestParam(required = false) Role role) {
        return adminService.listUsers(role);
    }

    @PutMapping("/users/{userId}/role")
    public AdminUserResponse updateUserRole(
        @PathVariable Long userId,
        @Valid @RequestBody UpdateUserRoleRequest request
    ) {
        return adminService.updateRole(userId, request.role());
    }

    @GetMapping("/assignments")
    public List<AssignmentResponse> listAssignments() {
        return adminService.listAssignments();
    }

    @PostMapping("/assignments")
    public ResponseEntity<AssignmentResponse> createAssignment(
        @Valid @RequestBody CreateAssignmentRequest request
    ) {
        AssignmentResponse response = adminService.assignPatient(request.doctorId(), request.patientId());
        return ResponseEntity.status(response.newlyCreated() ? HttpStatus.CREATED : HttpStatus.OK).body(response);
    }

    @DeleteMapping("/assignments/{doctorId}/{patientId}")
    public ResponseEntity<Void> deleteAssignment(
        @PathVariable Long doctorId,
        @PathVariable Long patientId
    ) {
        adminService.removeAssignment(doctorId, patientId);
        return ResponseEntity.noContent().build();
    }
}

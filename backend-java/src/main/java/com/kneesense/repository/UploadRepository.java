package com.kneesense.repository;

import com.kneesense.domain.Upload;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface UploadRepository extends JpaRepository<Upload, Long> {

    Optional<Upload> findByIdAndUser_Id(Long uploadId, Long userId);

    List<Upload> findAllByUser_IdOrderByCreatedAtDesc(Long userId);
}

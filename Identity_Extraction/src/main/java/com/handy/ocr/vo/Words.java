package com.handy.ocr.vo;

import lombok.Data;

import java.io.Serializable;

/**
 * @author hanshuai
 * @Description: {通用识别结果}
 * @date 2019/9/10
 */
@Data
public class Words implements Serializable {
    private String words;
    private Location location;
}

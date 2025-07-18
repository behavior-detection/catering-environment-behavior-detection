package com.handy.ocr.vo;

import lombok.Data;

import java.io.Serializable;

/**
 * @author hanshuai
 * @Description: {坐标}
 * @date 2019/9/10
 */
@Data
public class Location implements Serializable {
    private int top;
    private int left;
    private int width;
    private int height;
}

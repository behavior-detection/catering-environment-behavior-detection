package com.handy.ocr.vo.accurategeneral;

import com.handy.ocr.vo.Location;
import lombok.Data;

import java.io.Serializable;
import java.util.List;

/**
 * @author hanshuai
 * @Description: {通用文字识别(含位置高精度版本)}
 * @date 2019/9/10
 */
@Data
public class WordsResult implements Serializable {

    /**
     * 当前为四个顶点: 左上，右上，右下，左下。当vertexes_location=true时存在
     */
    private List<VertexesLocation> vertexes_location;
    /**
     * 识别结果字符串
     */
    private String words;

    /**
     * 位置数组（坐标0点为左上角）
     */
    private Location location;


    private List<VertexesLocation> finegrained_vertexes_location;

    private List<VertexesLocation> min_finegrained_vertexes_location;
}


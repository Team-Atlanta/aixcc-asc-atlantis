package com.code_intelligence.jazzer.mutation.fieldsemantic;

import static java.util.Arrays.stream;

import com.google.protobuf.Message.Builder;
import com.code_intelligence.jazzer.mutation.fieldsemantic.Mask;
import com.code_intelligence.jazzer.mutation.fieldsemantic.Encode;
import com.code_intelligence.jazzer.mutation.fieldsemantic.Checksum;
import com.code_intelligence.jazzer.mutation.fieldsemantic.Quantity;
import com.code_intelligence.jazzer.mutation.fieldsemantic.FieldSemantic;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Set;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Map.Entry;

/**
 * FieldSemanticsManager is a class that maintains the semantics of fields. The
 * field semantics are initialized from a JSON file, and can be dynamically
 * added or removed during runtime.
 * 
 * TODO: add bit field semantics
 */
public final class FieldSemanticsManager {

	private static HashMap<String, List<FieldSemantic>> semanticFieldMap = new HashMap<String, List<FieldSemantic>>();

	// input argument is a file
	// The csv format is [ (semantics name, semantic args) ]
	// for "mask", it should be ("mask", id)
	// for "encode", it should be ("encode", id, encodingType)
	public static void initFromCfgFile(String cfgFile) {
		// 1. parse the csv file
		// 2. for each field, add the semantics to the field
		System.out.println("Initializing field semantics from " + cfgFile + "...");
		System.out.flush();
		try {
			BufferedReader reader = new BufferedReader(new FileReader(cfgFile));
			reader.lines().forEach(line -> {
				if (line.strip().startsWith("#")) {
					// skip comment lines
					return;
				}

				String[] fields = line.strip().split(",");
				switch (fields[0].strip()) {
				case Mask.type:
					addOneFieldSemantic(fields[1].strip(), new Mask(fields[1].strip()));
					break;
				case Encode.type:
					addOneFieldSemantic(fields[1].strip(), new Encode(fields[1].strip(), fields[2].strip()));
					break;
				case Quantity.type:
					addOneFieldSemantic(fields[1].strip(), new Quantity(fields[1].strip(), fields[2].strip(), fields[3].strip()));
					break;
				default:
					throw new IllegalArgumentException("Unknown field semantic: " + fields[0]);
				}
			});
		} catch (IOException e) {
			// print error detail
			e.printStackTrace();
			throw new IllegalArgumentException("Failed to read the configuration file: " + cfgFile);
		}
		System.out.println("Successfully initialized field semantics from " + cfgFile);
		System.out.println(toDebugString());
		System.out.flush();
	}

	// dynamically add a field semantic to a field, for runtime LLM fuzzing guidance
	public static void addOneFieldSemantic(String id, FieldSemantic semantic) {
		if (!semanticFieldMap.containsKey(id)) {
			semanticFieldMap.put(id, new ArrayList<FieldSemantic>());
		}
		semanticFieldMap.get(id).add(semantic);
	}

	// dynamically remove a field semantic to a field, for runtime LLM fuzzing
	// guidance
	public static void removeOneFieldSemantic(String id, FieldSemantic semantic) {
		if (!semanticFieldMap.containsKey(id)) {
			return;
		}
		semanticFieldMap.get(id).remove(semantic);
	}

	public static String toDebugString() {
		StringBuilder sb = new StringBuilder();
		sb.append("Field semantics:\n");
		for (Entry<String, List<FieldSemantic>> entry : semanticFieldMap.entrySet()) {
			sb.append(entry.getKey());
			sb.append(": ");
			for (FieldSemantic semantic : entry.getValue()) {
				sb.append(semantic.getClass().getSimpleName());
				sb.append(" ");
			}
			sb.append("\n");
		}
		return sb.toString();
	}

	// Function summary: is a given field is masked during the mutation considering
	// its current semantics?
	// - A field can be directly masked by configuration or LLM fuzzing guidance
	// - A field can be indirectly masked according to its semantics such as it
	// contains the length of another field, or it is a checksum field
	// - Bit field can be masked only if all bits are masked
	public static boolean isFieldMasked(String id) {
		// id not exist -> not masked
		if (!semanticFieldMap.containsKey(id))
			return false;

		return semanticFieldMap.get(id).stream().anyMatch(semantic -> semantic.shouldMask());
	}

	public static boolean isFieldUnmasked(String id) {
		return !isFieldMasked(id);
	}

	private static <T extends Builder> void handleOneFieldValueInPlacePreMutation(String id,
			List<FieldSemantic> semantics, T reference) {
		// TODO: may semantics have conflict or priority?
		semantics.forEach(semantic -> semantic.fillPreMutationValueInPlace(reference));
	}

	private static <T extends Builder> void handleOneFieldValueInPlacePostMutation(String id,
			List<FieldSemantic> semantics, T reference) {
		// TODO: may semantics have conflict or priority?
		semantics.forEach(semantic -> semantic.fillPostMutationValueInPlace(reference));
	}

	// Function summary: fill the fields value according to the semantics after
	// mutation
	public static <T extends Builder> void fillFieldSemanticValueInPlacePreMutation(Set<String> idScope, T reference) {
		// iterate semanticFieldMap and fill the value
		semanticFieldMap.forEach((id, semantics) -> {
			if (idScope.contains(id))
				handleOneFieldValueInPlacePreMutation(id, semantics, reference);
		});
	}

	// Function summary: fill the fields value according to the semantics after
	// mutation
	public static <T extends Builder> void fillFieldSemanticValueInPlacePostMutation(Set<String> idScope, T reference) {
		// iterate semanticFieldMap and fill the value
		semanticFieldMap.forEach((id, semantics) -> {
			if (idScope.contains(id))
				handleOneFieldValueInPlacePostMutation(id, semantics, reference);
		});
	}

}

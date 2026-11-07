package generator_uml.back_generator_uml.service;

import generator_uml.back_generator_uml.entity.UmlClass;
import generator_uml.back_generator_uml.entity.UmlRelationship;
import generator_uml.back_generator_uml.entity.UmlSchema;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * Names of the fields that each relationship adds to the generated classes.
 *
 * <p>A field used to be named after the class at the other end ({@code empleado}, {@code departamento}), so a recursive
 * association (a class related to itself) or two relationships between the same two classes put two fields with the same
 * name in one class and the generated project did not compile. The names are the same as before when nothing clashes;
 * only a clash changes them: a recursive 1:N association gets {@code padre} and {@code hijos}, a recursive N:M gets
 * {@code origen} and {@code destino} in the join entity, and any other repeated name gets a number ({@code aeropuerto2}).
 * Names stay lowercase without separators, as the rest of the generated fields: the Flutter generator reads the JSON keys
 * that way and applies the same rules.
 *
 * <p>Both the project generator and the Postman collection generator ask this class, so the keys of the sample request
 * bodies match the fields of the entities.
 */
final class RelationNaming {

    /** Fields one relationship adds. A side is {@code null} when the relationship adds nothing to that class. */
    static final class Names {
        /** Field added to the source class: a reference (N:1, 1:1) or a collection (1:N, and N:M to the join entity). */
        String sourceSide;
        /** Field added to the target class. */
        String targetSide;
        /** N:M only: the join entity's field that points to the source class. */
        String joinToSource;
        /** N:M only: the join entity's field that points to the target class. */
        String joinToTarget;
    }

    private RelationNaming() {
    }

    static boolean isAssociationLike(String type) {
        return "association".equals(type) || "aggregation".equals(type)
                || "composition".equals(type) || "dependency".equals(type);
    }

    /**
     * {@code [sourceIsMany, targetIsMany]} with the defaults the entity generator applies: an empty source multiplicity
     * counts as many, an empty target as one, and a dependency is never 1..1.
     */
    static boolean[] manyFlags(UmlRelationship rel) {
        String rawSource = (rel.getLabels() != null && rel.getLabels().size() > 0 && rel.getLabels().get(0) != null)
                ? rel.getLabels().get(0).trim() : "";
        String rawTarget = (rel.getLabels() != null && rel.getLabels().size() > 1 && rel.getLabels().get(1) != null)
                ? rel.getLabels().get(1).trim() : "";
        String sourceCard = rawSource.isEmpty() ? "*" : rawSource;
        String targetCard = rawTarget.isEmpty() ? "1" : rawTarget;
        if ("dependency".equals(rel.getType()) && rawSource.isEmpty() && rawTarget.isEmpty()) {
            sourceCard = "*";
            targetCard = "1";
        }
        boolean sourceIsMany = sourceCard.contains("*");
        boolean targetIsMany = targetCard.contains("*");
        if ("dependency".equals(rel.getType()) && !sourceIsMany && !targetIsMany) {
            sourceIsMany = true;
        }
        return new boolean[]{sourceIsMany, targetIsMany};
    }

    /** The names for every association-like relationship, by its position in {@code schema.getRelationships()}. */
    static Map<Integer, Names> assign(UmlSchema schema) {
        Map<Integer, Names> result = new HashMap<>();
        if (schema.getRelationships() == null) {
            return result;
        }
        Map<String, Set<String>> usedByClass = new HashMap<>();
        int index = -1;
        for (UmlRelationship rel : schema.getRelationships()) {
            index++;
            if (!isAssociationLike(rel.getType())) {
                continue;
            }
            UmlClass source = classById(schema, rel.getSourceId());
            UmlClass target = classById(schema, rel.getTargetId());
            if (source == null || target == null) {
                continue;
            }
            String sourceEntity = NamingUtil.toJavaClass(source.getName());
            String targetEntity = NamingUtil.toJavaClass(target.getName());
            boolean recursive = source.getId().equals(target.getId());
            boolean[] many = manyFlags(rel);
            boolean sourceIsMany = many[0];
            boolean targetIsMany = many[1];

            Names names = new Names();
            if (sourceIsMany && targetIsMany) {
                String first = sourceEntity.compareTo(targetEntity) < 0 ? sourceEntity : targetEntity;
                String second = sourceEntity.compareTo(targetEntity) < 0 ? targetEntity : sourceEntity;
                String joinField = NamingUtil.toField(first + second);
                names.joinToSource = recursive ? "origen" : NamingUtil.toField(sourceEntity);
                names.joinToTarget = recursive ? "destino" : NamingUtil.toField(targetEntity);
                names.sourceSide = unique(usedByClass, source.getId(), recursive ? joinField + "origen" : joinField);
                names.targetSide = unique(usedByClass, target.getId(), recursive ? joinField + "destino" : joinField);
            } else if (sourceIsMany) {
                // source *..1 target: the source holds the reference, the target holds the collection
                names.sourceSide = unique(usedByClass, source.getId(), recursive ? "padre" : NamingUtil.toField(targetEntity));
                names.targetSide = unique(usedByClass, target.getId(), recursive ? "hijos" : NamingUtil.toField(sourceEntity));
            } else if (targetIsMany) {
                // source 1..* target: the source holds the collection, the target holds the reference
                names.sourceSide = unique(usedByClass, source.getId(), recursive ? "hijos" : NamingUtil.toField(targetEntity));
                names.targetSide = unique(usedByClass, target.getId(), recursive ? "padre" : NamingUtil.toField(sourceEntity));
            } else {
                // 1..1: only the source holds a reference
                names.sourceSide = unique(usedByClass, source.getId(), NamingUtil.toField(targetEntity));
            }
            result.put(index, names);
        }
        return result;
    }

    /** {@code set} + the field name with its first letter in capitals, as Lombok names the setter. */
    static String setterFor(String field) {
        return "set" + Character.toUpperCase(field.charAt(0)) + field.substring(1);
    }

    private static UmlClass classById(UmlSchema schema, String id) {
        return schema.getClasses().stream().filter(c -> c.getId().equals(id)).findFirst().orElse(null);
    }

    private static String unique(Map<String, Set<String>> usedByClass, String classId, String base) {
        Set<String> taken = usedByClass.computeIfAbsent(classId, k -> new HashSet<>());
        String name = base;
        for (int n = 2; !taken.add(name); n++) {
            name = base + n;
        }
        return name;
    }
}

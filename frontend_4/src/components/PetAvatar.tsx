import defaultPetImage from "../assets/dog-head-profile.svg";
import type { Pet } from "../domain/types";

interface PetAvatarProps {
  pet: Pet;
  size?: "small" | "medium" | "large";
}

export function PetAvatar({ pet, size = "medium" }: PetAvatarProps): React.JSX.Element {
  return (
    <img
      className="pet-avatar"
      data-size={size}
      src={pet.image ?? defaultPetImage}
      alt={`Retrato de ${pet.name}`}
      onError={({ currentTarget }) => {
        if (currentTarget.src !== defaultPetImage) currentTarget.src = defaultPetImage;
      }}
      width={size === "large" ? 112 : size === "medium" ? 48 : 36}
      height={size === "large" ? 112 : size === "medium" ? 48 : 36}
    />
  );
}
